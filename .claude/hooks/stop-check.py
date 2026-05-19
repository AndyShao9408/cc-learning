#!/usr/bin/env python3
"""Stop hook: 交付验收 — 代码/配置/文档改动后必须有验证结果才允许结束。"""

import json
import sys
import re

# ---------------------------------------------------------------------------
# 文件改动信号 — 通过这些工具修改了文件
# ---------------------------------------------------------------------------
MODIFY_TOOLS = {"Edit", "Write"}

# ---------------------------------------------------------------------------
# 验证信号 — 在 transcript 中匹配以下模式即视为已做验证
# ---------------------------------------------------------------------------
VERIFY_PATTERNS = [
    # 测试运行
    r"\b(pytest|npm\s+test|npm\s+run\s+test|npx\s+vitest|npx\s+ava)\b",
    r"\b(go\s+test|cargo\s+test|mix\s+test|rails\s+test)\b",
    r"\b(jest|mocha|jasmine|karma)\b",
    r"\b(npx\s+playwright\s+test|npx\s+cypress\s+run)\b",
    r"\b(python\s+-m\s+pytest|python\s+-m\s+unittest)\b",
    r"\bdotnet\s+test\b",
    r"\b(test\s+passed|tests?\s+passed|all\s+tests?\s+pass)\b",
    r"\b(\d+\s+passed.*\d+\s+failed|\d+\s+spec.*\d+\s+fail)\b",
    r"\btest\s+suite.*passed\b",

    # Lint 检查
    r"\b(eslint|prettier|oxlint|biome\s+lint|standard)\b",
    r"\b(pylint|ruff\s+check|flake8|black\s+--check|isort\s+--check)\b",
    r"\b(clippy|shellcheck|hadolint)\b",
    r"\b(lint\s+passed|lint\s+check.*pass|linting.*pass)\b",
    r"\bno\s+lint(ing)?\s+(errors|issues|warnings|problems)\b",

    # 类型检查
    r"\b(mypy|pyright|pytype|tsc\b|tsc\s+--noEmit|npx\s+tsc)\b",
    r"\b(type-?check|typecheck)\s+(passed|done|complete|clean)\b",
    r"\bno\s+type\s+errors\b",
    r"\btypecheck.*success\b",

    # 功能验证说明 (中文/英文)
    r"功能验证[：:].*[通过✓✅成]",
    r"验证[通过✓✅]",
    r"\b(verified|validated|confirmed\s+working)\b",
    r"\bmanually\s+(tested|verified|checked)\b",
    r"\bworks?\s+(correctly|as\s+expected|fine)\b",
    r"\b(functional|manual)\s+(test|verification)\s+(passed|done|ok)\b",
    r"\bgolden\s+path\b",

    # 检查/确认语句
    r"我已经?\s*(验证|测试|检查|确认|确保)",
    r"(已|已经|have)\s*(验证|测试|检查|确认)(过|了)?\s*(功能|代码|效果|无误)",
    r"\[.*\]\s*(验证|测试|检查).*(通过|完成|OK|ok|done)",
    r"验收\s*(通过|完成)|\bdelivery\s+check\b",
]


def is_system_message(msg: dict) -> bool:
    """Skip system-level messages that aren't real user/assistant turns."""
    role = msg.get("role", "")
    if role == "system":
        return True
    return False


def extract_text(msg: dict) -> str:
    """Extract all text from a message regardless of content format."""
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict):
                t = block.get("text", "") or block.get("content", "")
                if isinstance(t, str):
                    texts.append(t)
                # tool_use block — capture tool name + inputs
                if block.get("type") == "tool_use":
                    texts.append(json.dumps(block, ensure_ascii=False))
                # tool_result block
                if block.get("type") == "tool_result":
                    texts.append(json.dumps(block, ensure_ascii=False))
        return " ".join(texts)
    return ""


def detect_modifications(messages: list[dict]) -> set[str]:
    """Find files modified via Edit/Write tool calls."""
    changed = set()
    for msg in messages:
        content = msg.get("content", "")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") in MODIFY_TOOLS:
                inp = block.get("input", {})
                path = inp.get("file_path", "")
                if path:
                    changed.add(path)
    return changed


def detect_verification(messages: list[dict]) -> bool:
    """Check whether verification evidence exists anywhere in the transcript."""
    combined = ""
    for msg in messages:
        combined += " " + extract_text(msg)

    for pat in VERIFY_PATTERNS:
        if re.search(pat, combined, re.IGNORECASE):
            return True
    return False


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        # No input — conservative: allow stop
        sys.exit(0)

    messages: list[dict] = []
    try:
        # Try JSONL (one JSON object per line)
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                pass

        # If JSONL parsing got nothing, try single JSON array
        if not messages:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                messages = parsed
    except (json.JSONDecodeError, Exception):
        pass

    # Filter out system messages
    messages = [m for m in messages if not is_system_message(m)]

    changed = detect_modifications(messages)
    verified = detect_verification(messages)

    if changed and not verified:
        print()
        print("=" * 60)
        print("  STOP HOOK — 交付验收未通过")
        print("=" * 60)
        print()
        print("  检测到以下文件被修改：")
        for f in sorted(changed):
            print(f"    · {f}")
        print()
        print("  但本轮对话中未发现以下任一验证完成的证据：")
        print("    - 测试运行 (pytest, jest, go test, ...)")
        print("    - Lint 检查 (eslint, ruff, oxlint, ...)")
        print("    - 类型检查 (mypy, tsc, pyright, ...)")
        print("    - 功能验证 / 手动验证说明")
        print()
        print("  请完成验证后再结束本轮对话。")
        print("=" * 60)
        print()
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
