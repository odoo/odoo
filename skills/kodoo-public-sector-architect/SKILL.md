---
name: kodoo-public-sector-architect
description: Shape the architecture of Kodoo's public administration suite. Use when Codex works on `gov_*` modules or adjacent process-heavy modules, especially to model interlinked government workflows, institutional entities, budgeting, procurement, protocol, contracts, compliance, and domain boundaries without leaking `gov_*` into clean `br_*` foundations.
---

# Kodoo Public Sector Architect

## Overview

Design public-sector modules as a coherent institutional system instead of a pile of isolated forms. Keep government workflows connected without collapsing domain boundaries.

## Quick Start

1. Identify the dominant institutional entity:
   process, requisition, procurement, contract, protocol, commitment, budget item, document, asset, or fiscal year.
2. Identify the interaction model:
   process-centric, document-centric, case-centric, workflow-oriented, or protocol-driven.
3. Decide whether the change belongs in a domain app, shared framework, or process layer.
4. Check whether the design would accidentally turn `gov_*` into a hidden base for `br_*`.

## Analyze First

1. Central entities and lifecycle ownership.
2. Workflow handoffs between modules and departments.
3. Module topology:
   vertical apps, shared institutional framework, or hybrid sliced architecture.
4. Auditability, traceability, and compliance constraints.

## Responsibilities

- Prevent accidental monolith sprawl.
- Keep public-sector contextualization in `gov_*`.
- Clarify which modules are reusable infrastructure versus domain-specific applications.
- Preserve separation from `br_*` foundations.

## Output Shape

- Domain-slice recommendation.
- Entity and workflow map.
- Suggested module boundaries.
- Coupling warnings.
- Missing institutional primitives.

## Guardrails

- Never turn `gov_*` into the hidden base for `br_*`.
- Do not force all workflows into one oversized module.
- Preserve auditability and traceability as first-class concerns.
