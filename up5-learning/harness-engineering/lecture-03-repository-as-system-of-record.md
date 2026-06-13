# Lecture 03 — Why the Repository Must Be the System of Record

Source: https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-03-why-the-repository-must-become-the-system-of-record/

## Core insight

An agent's reality is bounded by what is in the repository. Decisions in Slack,
context in Confluence, conventions in someone's head — **these do not exist for the agent**.

> "The repo has the final say."

## Key terms

| Term | Definition |
|---|---|
| **Knowledge Visibility Gap** | % of project knowledge absent from the repo — larger gap = higher failure rate |
| **Fresh Session Test** | 5 questions a new agent must answer using only repo contents |
| **Discovery Cost** | Context budget consumed locating info instead of doing the task |
| **Knowledge Decay Rate** | % of repo knowledge becoming stale over time |
| **System of Record** | The repo is authoritative for decisions, architecture, state, and verification |

## Fresh Session Test (5 questions)

A new agent session should be able to answer all five from the repo alone:

1. What is this system?
2. How is it organised?
3. How do I run it?
4. How do I verify it?
5. What is the current progress?

## Four principles for a good map

| Principle | Rule |
|---|---|
| **Proximity** | Docs belong next to the code they describe (`addons/<module>/NOTES.md`) |
| **Standardised entry** | `CLAUDE.md` answers Q1–Q4 in ~100 lines |
| **Minimal completeness** | Only what has a clear use case — but all 5 questions must be answerable |
| **Synchronised updates** | Docs change in the same commit as the code they describe |

## ACID state management

| Property | Rule |
|---|---|
| **Atomicity** | One logical change per commit; `git stash` incomplete work |
| **Consistency** | `./verify.sh <module>` passes before every commit |
| **Isolation** | One branch per feature or fix |
| **Durability** | All decisions live in git-tracked files, not session memory |

## How this maps to `odoo-up5`

| Gap | Fix applied |
|---|---|
| Q1 failed — no project identity | Added **Project Identity** section to `CLAUDE.md` with team placeholder |
| No proximity docs | Added `NOTES.md` template in `up5-docs/architecture/` + layout note in `CLAUDE.md` |
| No ACID rules | Added **State Management (ACID)** section to `CLAUDE.md` |
| Repository Layout missing key files | Updated layout to show `claude-progress.md`, `feature_list.json`, and `NOTES.md` |

## Warning: knowledge decay

Outdated documentation is **worse than no documentation** — it actively misleads.
Rule: if you change behaviour, update the adjacent `NOTES.md` in the same commit.
