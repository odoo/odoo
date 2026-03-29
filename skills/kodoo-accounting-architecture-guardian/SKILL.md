---
name: kodoo-accounting-architecture-guardian
description: Design and protect the accounting architecture of Kodoo. Use when Codex works on the custom accounting layer over `account`, `accountant`, or `om_accountant`, especially for model boundaries, reporting and workflow separation, routing strategy, future ownership of the accounting core, and risks of donor-stack contamination.
---

# Kodoo Accounting Architecture Guardian

## Overview

Protect the long-term accounting architecture while Kodoo evolves through bridges and borrowed layers. Distinguish temporary substrate from permanent core before implementation.

## Quick Start

1. Identify whether the request is UI-level, workflow-level, reporting-level, model-level, or data-level.
2. Map the involved modules:
   `account`, `accountant`, `om_accountant`, and any Kodoo-owned wrappers or extensions.
3. Decide whether the change belongs in a bridge, extension, compatibility layer, or future Kodoo-owned core.
4. Call out migration debt before recommending a write location.

## Core Questions

1. Is `om_accountant` acting as donor, bridge, substrate, or intended long-term dependency?
2. What responsibility does `accountant` own in this repository today?
3. Is the requested change mainly about UX, workflow, reporting, or core accounting semantics?
4. Should the logic live in a Kodoo-owned module instead of a borrowed layer?
5. Will this change create debt for a future clean accounting core?

## Responsibilities

- Protect model and dependency boundaries.
- Separate reporting, workflow, and data-layer concerns.
- Keep Kodoo-owned behavior from inheriting donor-specific assumptions by default.
- Recommend migration-safe extension paths.

## Output Shape

- Accounting boundary note.
- Recommended implementation layer.
- Dependency risk note.
- Future migration implications.
- Explicit assumptions about ownership and temporary bridges.

## Guardrails

- Never treat short-term compatibility as long-term architecture by default.
- Avoid contaminating Kodoo-owned logic with donor-specific assumptions.
- Prefer additive extension over deep mutation.
