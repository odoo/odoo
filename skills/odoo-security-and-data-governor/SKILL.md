---
name: odoo-security-and-data-governor
description: Review and implement Odoo security, ACLs, record rules, data files, and migration-sensitive model changes. Use when Codex adds user-facing models, changes access boundaries, introduces sensitive government or accounting records, or needs to protect upgrade-safe data evolution across manifests, XML, CSV, and model fields.
---

# Odoo Security and Data Governor

## Overview

Protect access control, data integrity, and upgrade safety. Keep new functionality from silently bypassing permissions, exposing sensitive records, or creating schema debt.

## Quick Start

1. List every new or changed user-facing surface:
   model, wizard, menu, action, view, report, or data file.
2. Check whether ACLs, record rules, and group restrictions already cover that surface.
3. Check whether the change affects default data, `noupdate`, field evolution, or multi-company behavior.
4. Recommend additive changes before destructive ones.

## Review Areas

1. `ir.model.access.csv`
2. Record rules and group scopes.
3. Menu and action group restrictions.
4. Default data and `noupdate` behavior.
5. Model field evolution and backward compatibility.
6. Multi-company implications.
7. Sensitive document and record access paths.

## Responsibilities

- Add or adjust ACLs when needed.
- Ensure user-facing features have coherent permissions.
- Flag risky schema or data evolution.
- Protect upgrade paths and backward compatibility.
- Reduce accidental overexposure.

## Output Shape

- Security impact note.
- Access rule changes.
- Data migration risk note.
- Backward compatibility note.

## Guardrails

- Never expose a menu or model without checking permissions.
- Never assume admin-only access is acceptable unless explicit.
- Avoid destructive schema changes when additive evolution is possible.
