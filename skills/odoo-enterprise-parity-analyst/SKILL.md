---
name: odoo-enterprise-parity-analyst
description: Analyze and design Kodoo features that intentionally mimic Odoo Enterprise interaction patterns. Use when Codex must determine whether to reproduce behavioral, visual, navigational, or API parity with Odoo Enterprise, especially around accounting flows, dashboards, menus, actions, views, and other user-facing paths where familiarity matters.
---

# Odoo Enterprise Parity Analyst

## Overview

Decide what should match Odoo Enterprise, what should only feel familiar, and what should remain Kodoo-specific. Preserve user fluency without surrendering architectural control.

## Quick Start

1. Identify the target flow:
   menu entry, action, dashboard, list or form view, wizard, report, or API contract.
2. Separate parity into four axes:
   behavioral, visual, navigational, and API/model.
3. Determine whether the request needs exact parity, selective parity, or symbolic familiarity.
4. Trace the narrowest layer that can create the desired familiarity without copying upstream structure unnecessarily.

## Analyze Across Four Axes

1. Behavioral parity:
   compare workflow steps, state transitions, defaults, and user expectations.
2. Visual parity:
   compare labels, layout density, grouping, view composition, and dashboard affordances.
3. Navigational parity:
   compare entry points, menus, breadcrumbs, actions, and how the user reaches the flow.
4. API and model parity:
   compare model semantics, extension contracts, method expectations, and integration touchpoints.

## Recommend a Strategy

- Recommend `exact` when downstream expectations, training costs, or integration contracts depend on a close match.
- Recommend `selective` when the user experience should feel native but Kodoo should keep its own module or model boundaries.
- Recommend `symbolic` when only surface familiarity is needed and deep parity would create debt.

## Output Shape

- What should match Enterprise exactly.
- What should feel familiar without being identical.
- What should remain Kodoo-specific.
- Risk of shallow mimicry versus deep compatibility.
- Recommended parity strategy:
  exact, selective, or symbolic.
- Recommended narrowest implementation surface.

Distinguish evidence from inference. Name the concrete menus, actions, views, models, or contracts that drive the recommendation.

## Guardrails

- Never assume parity is always desirable.
- Never propose vendor edits first.
- Do not confuse UI similarity with model compatibility.
- Prefer the smallest parity surface that preserves user fluency.
