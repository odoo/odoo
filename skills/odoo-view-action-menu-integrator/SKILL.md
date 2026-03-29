---
name: odoo-view-action-menu-integrator
description: Implement or refactor Odoo user-facing integration points such as menus, actions, window actions, server actions, inherited views, dashboards, and navigation flows. Use when Codex must make custom modules feel coherent and native without rewriting entire views, especially when rerouting features through existing entry points.
---

# Odoo View Action Menu Integrator

## Overview

Specialize in the user-facing glue of Odoo: menus, actions, views, dashboards, and navigation. Make Kodoo modules feel integrated without brittle full replacements.

## Quick Start

1. Trace the current chain:
   menu -> action -> view -> model or method.
2. Identify the narrowest inheritance or routing point that can produce the desired UX.
3. Prefer extending existing XML IDs over creating parallel navigation.
4. Validate visibility, domains, and groups before closing the task.

## Preferred Approach

1. Inspect the original action, menu, and view chain.
2. Identify the smallest precise inheritance point.
3. Prefer small XPath changes over replacing entire views.
4. Preserve XML IDs and surrounding grouping when possible.
5. Keep labels, grouping, and navigation consistent with nearby modules.

## Responsibilities

- Maintain menu hierarchy coherence.
- Keep action routing correct.
- Preserve view inheritance precision.
- Clarify dashboard entry points.
- Avoid duplicate or conflicting navigation.

## Validate

- XML integrity.
- Action IDs, domains, and context.
- Menu visibility and group restrictions.
- Install or upgrade sanity when the routing changed materially.

## Guardrails

- Avoid full view copy unless absolutely necessary.
- Do not create duplicate menus or conflicting actions.
- Do not change UX flow without checking surrounding modules.
