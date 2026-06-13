# Lecture 04 — Why One Giant Instruction File Fails

Source: https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-04-why-one-giant-instruction-file-fails/

## Core insight

A bloated instruction file actively harms agent performance. More content ≠ better guidance.

> "The entry file is a router, not an encyclopedia."

## The vicious cycle

1. **Context budget exhaustion** — a 600-line file consumes 10-20K tokens, leaving less room for actual work
2. **Lost in the middle** — LLMs process extremes better than the middle (Liu et al. 2023); critical constraints buried mid-file get ignored
3. **Priority confusion** — hard constraints and historical notes look identical; agents can't distinguish non-negotiable from suggestive
4. **Maintenance decay** — files only grow; deleting feels risky; signal-to-noise declines
5. **Contradiction accumulation** — rules added over time conflict; agents pick randomly

## Key concepts

| Term | Definition |
|---|---|
| **Instruction bloat** | 10–15% context window use begins crowding productive reasoning |
| **Signal-to-noise ratio** | Proportion of instructions relevant to the current task |
| **Entry file** | 50–200 line routing document; links to topic docs |
| **Reveal on demand** | Progressive disclosure — load detail only when needed |

## Solution architecture

**Entry file (`CLAUDE.md`):** project identity + max 15 global hard constraints + links to topic docs

**Topic documents (50–150 lines each):** one per subject area, loaded on demand

Every instruction should have:
- Why the rule exists
- When it applies
- When it can be removed

## Real-world results

SaaS team: 600 lines → 80 lines + topic docs
- Task success: 45% → 72%
- Security constraint compliance: 60% → 95%

## How this maps to `odoo-up5`

| Before | After |
|---|---|
| `CLAUDE.md` 294 lines, 1743 words | `CLAUDE.md` ~90 lines — router only |
| Conventions buried in middle | Moved to `up5-docs/standards/odoo-conventions.md` |
| Detailed test commands in CLAUDE.md | Moved to `up5-docs/setup/dev-environment.md` |
| Hard constraints mixed with guidelines | Top section, numbered, max 10 |
| Coding conventions duplicated | Single authoritative source in `odoo-conventions.md` |

## Strategic instruction placement

Critical constraints go at the **top** of CLAUDE.md (Startup Checklist, Hard Constraints, Definition of Done) — never in the middle where they get lost.
