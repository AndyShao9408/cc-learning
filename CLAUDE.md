# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**重要：永远使用中文回复用户。**

## What this project is

This is a **Claude Code skills workspace** — not a traditional software project. It's a local sandbox for learning and configuring Claude Code's extensibility features: skills, custom agents, and hooks. There is no application code, build system, or test suite here.

## Directory structure

```
.claude/
  settings.json           # Project-level hooks config
  settings.local.json     # Local permission overrides (not committed)
  agents/                 # Custom agent definitions
  hooks/                  # Hook scripts (Stop hook, etc.)
  memory/                 # Persistent project memory
  agent-memory/           # Per-agent persistent memory stores
.agents/
  skills/                 # Cached skill files from anthropics/skills (GitHub)
skills-lock.json          # Manifest of installed skills with version hashes
```

## Skills

Skills are loaded from `anthropics/skills` on GitHub and cached in `.agents/skills/`. The manifest at `skills-lock.json` tracks each skill's source, path, and content hash. Skills are managed by Claude Code's built-in skill system — do not manually edit `.agents/skills/` files. The 20+ skills cover topics from frontend design and algorithmic art to Claude API usage in multiple languages (Python, TypeScript, Go, Java, etc.).

## Custom agents

Custom agents are defined as markdown files in `.claude/agents/` and surfaced to the Agent tool. Currently:
- `evidence-researcher` — Chinese-language research agent for verifying facts and preparing briefs. Uses sonnet model, pink color label.

## Hooks

A **Stop hook** is configured in `.claude/settings.json` to run `.claude/hooks/stop-check.py` on every session stop. This hook:
- Scans the transcript for file modifications (Edit/Write tool calls)
- Checks for verification evidence (test runs, lint checks, type checks, or explicit verification statements)
- **Blocks session stop** if files were modified but no verification was detected

The hook works with any language/tool (pytest, jest, go test, eslint, ruff, mypy, tsc, etc.) via regex patterns. It parses JSONL transcript input from stdin.

## Local settings

`.claude/settings.local.json` is for local overrides not intended for sharing. Currently it only allows `WebSearch`. File-based permissions (allow/deny lists) go here.
