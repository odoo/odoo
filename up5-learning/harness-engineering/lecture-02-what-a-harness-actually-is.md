# Lecture 02 — What a Harness Actually Is

Source: https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-02-what-a-harness-actually-is/

## Core insight

A harness is not just a prompt file. It is **five interconnected subsystems**, each with a distinct responsibility. Any missing subsystem creates a gap that limits how much model capability gets realized.

> "Everything in engineering infrastructure outside model weights determines how much capability gets actualized."

## The Five Subsystems

| # | Subsystem | What it provides |
|---|---|---|
| 1 | **Instruction** | `CLAUDE.md` / `AGENTS.md` — project overview, constraints, tech stack, first-run commands |
| 2 | **Tool** | Shell access, file read/write, git — least-privilege but sufficient |
| 3 | **Environment** | Locked dependencies, runtime spec (`.python-version`, `pyproject.toml`) |
| 4 | **State** | `claude-progress.md`, `feature_list.json` — read on start, updated before close |
| 5 | **Feedback** | Explicit verification commands — **highest ROI subsystem** |

## Real-world impact (TypeScript/React, 20k LOC)

| Stage | What was added | Success rate |
|---|---|---|
| 1 | Basic README | 20% |
| 2 | AGENTS.md | 60% |
| 3 | **Verification commands** | **80%** |
| 4 | Progress templates | 80–100% |

No model changes. Verification commands alone drove 20 percentage points of gain.

## Auditing a harness (Five-Tuple)

Score each subsystem 1–5. Fix the lowest scorer first.

**Design principle:** Enforce invariants, don't micromanage implementation.
**Maintenance:** Harnesses deteriorate like code — audit regularly to prevent harness debt.

## How this maps to `odoo-up5`

| Subsystem | Implementation | Score |
|---|---|---|
| Instruction | `CLAUDE.md` — Odoo conventions, definition of done, diagnostic loop | 4/5 |
| Tool | Git Bash, conda, python, ruff all accessible | 4/5 |
| Environment | `conda env odoo19` + `requirements.txt` + `.python-version` | 4/5 |
| State | `claude-progress.md` + `feature_list.json` with criteria | 4/5 |
| Feedback | `verify.sh` (lint + tests), `ruff.toml` at repo root | 4/5 |

## Changes made after this lecture

- Added `.python-version` → runtime spec for the Environment subsystem
- Added `verify.sh` → single command for lint + tests (Feedback subsystem)
- Updated `CLAUDE.md` → surfaced `verify.sh` as the primary verification command
- Updated Definition of Done → requires `verify.sh` output, not just passing tests
