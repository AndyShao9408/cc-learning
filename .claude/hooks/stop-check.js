#!/usr/bin/env node
"use strict";

const MODIFY_TOOLS = new Set(["Edit", "Write"]);

const VERIFY_PATTERNS = [
  // test run
  /\b(pytest|npm\s+test|npm\s+run\s+test|npx\s+vitest|npx\s+ava)\b/i,
  /\b(go\s+test|cargo\s+test|mix\s+test|rails\s+test)\b/i,
  /\b(jest|mocha|jasmine|karma)\b/i,
  /\b(npx\s+playwright\s+test|npx\s+cypress\s+run)\b/i,
  /\b(python\s+-m\s+pytest|python\s+-m\s+unittest)\b/i,
  /\bdotnet\s+test\b/i,
  /\b(test\s+passed|tests?\s+passed|all\s+tests?\s+pass)\b/i,
  /\b(\d+\s+passed.*\d+\s+failed|\d+\s+spec.*\d+\s+fail)\b/i,
  /\btest\s+suite.*passed\b/i,

  // lint
  /\b(eslint|prettier|oxlint|biome\s+lint|standard)\b/i,
  /\b(pylint|ruff\s+check|flake8|black\s+--check|isort\s+--check)\b/i,
  /\b(clippy|shellcheck|hadolint)\b/i,
  /\b(lint\s+passed|lint\s+check.*pass|linting.*pass)\b/i,
  /\bno\s+lint(ing)?\s+(errors|issues|warnings|problems)\b/i,

  // type check
  /\b(mypy|pyright|pytype|tsc\b|tsc\s+--noEmit|npx\s+tsc)\b/i,
  /\b(type-?check|typecheck)\s+(passed|done|complete|clean)\b/i,
  /\bno\s+type\s+errors\b/i,
  /\btypecheck.*success\b/i,

  // functional / manual verification
  /功能验证[：:].*[通过✓✅成]/,
  /验证[通过✓✅]/,
  /\b(verified|validated|confirmed\s+working)\b/i,
  /\bmanually\s+(tested|verified|checked)\b/i,
  /\bworks?\s+(correctly|as\s+expected|fine)\b/i,
  /\b(functional|manual)\s+(test|verification)\s+(passed|done|ok)\b/i,
  /\bgolden\s+path\b/i,

  // check / confirm statements
  /我已经?\s*(验证|测试|检查|确认|确保)/,
  /(已|已经|have)\s*(验证|测试|检查|确认)(过|了)?\s*(功能|代码|效果|无误)/,
  /\[.*\]\s*(验证|测试|检查).*(通过|完成|OK|ok|done)/,
  /验收\s*(通过|完成)|\bdelivery\s+check\b/,
];

function isSystemMessage(msg) {
  return msg.role === "system";
}

function extractText(msg) {
  const content = msg.content;
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((block) => {
        if (typeof block === "string") return block;
        if (typeof block === "object" && block !== null) {
          if (block.type === "tool_use" || block.type === "tool_result") {
            return JSON.stringify(block);
          }
          return block.text || block.content || "";
        }
        return "";
      })
      .join(" ");
  }
  return "";
}

function detectModifications(messages) {
  const changed = new Set();
  for (const msg of messages) {
    const content = msg.content;
    if (!Array.isArray(content)) continue;
    for (const block of content) {
      if (!block || typeof block !== "object") continue;
      if (block.type === "tool_use" && MODIFY_TOOLS.has(block.name)) {
        const path = block.input?.file_path;
        if (path) changed.add(path);
      }
    }
  }
  return changed;
}

function detectVerification(messages) {
  const combined = messages.map(extractText).join(" ");
  for (const pat of VERIFY_PATTERNS) {
    if (pat.test(combined)) return true;
  }
  return false;
}

function main() {
  const chunks = [];
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => chunks.push(chunk));
  process.stdin.on("end", () => {
    const raw = chunks.join("").trim();

    if (!raw) {
      process.exit(0);
    }

    let messages = [];

    // Try JSONL
    for (const line of raw.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        messages.push(JSON.parse(trimmed));
      } catch {
        // not valid JSON, skip
      }
    }

    // If JSONL got nothing, try single JSON array
    if (messages.length === 0) {
      try {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) messages = parsed;
      } catch {
        // not valid JSON, skip
      }
    }

    messages = messages.filter((m) => !isSystemMessage(m));

    const changed = detectModifications(messages);
    const verified = detectVerification(messages);

    if (changed.size > 0 && !verified) {
      console.log();
      console.log("=".repeat(60));
      console.log("  STOP HOOK — 交付验收未通过");
      console.log("=".repeat(60));
      console.log();
      console.log("  检测到以下文件被修改：");
      for (const f of [...changed].sort()) {
        console.log(`    · ${f}`);
      }
      console.log();
      console.log("  但本轮对话中未发现以下任一验证完成的证据：");
      console.log("    - 测试运行 (pytest, jest, go test, ...)");
      console.log("    - Lint 检查 (eslint, ruff, oxlint, ...)");
      console.log("    - 类型检查 (mypy, tsc, pyright, ...)");
      console.log("    - 功能验证 / 手动验证说明");
      console.log();
      console.log("  请完成验证后再结束本轮对话。");
      console.log("=".repeat(60));
      console.log();
      process.exit(1);
    }

    process.exit(0);
  });
}

main();
