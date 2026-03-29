---
name: repo-cartographer
description: Map the Kodoo repository before implementation. Use when Codex needs to inspect addon families, module boundaries, donor stacks, manifest dependencies, inherited models and views, menus and actions, security files, tests, and likely extension points before editing code, especially around `custom_addons/`, `account`, `accountant`, `om_accountant`, `gov_*`, `br_*`, `knowledge/*`, or shared infrastructure.
---

# Repo Cartographer

## Overview

Reverse-engineer the relevant part of the repository before making changes. Build a practical architectural map that reduces false assumptions, hidden coupling, namespace drift, and edits in the wrong layer.

## Quick Start

1. Read the local guidance first: `AGENTS.md`, `README.md` when relevant, and `skills/odoo-19-custom-addons-developer/references/repo-guide.md` when repo-specific commands or addon-family boundaries matter.
2. Identify the candidate module family before reading deeply:
   `custom_addons/` project-owned by default, `addons/` upstream vendor code, `custom_addons/om_account_accountant-19.0.1.0.3` vendored third-party, `knowledge/*` OCA-style structure, `gov_*` public-sector project modules, `br_*` Brazilian foundation modules.
3. Read the target module's `__manifest__.py`, `__init__.py`, nearby `models/`, `views/`, `security/`, `data/`, and `tests/` before inferring ownership or extension points.
4. Trace the runtime path end to end:
   menu or action -> view -> model or method -> security -> related data or tests.
5. Deliver an interpreted map, not a raw file dump.

## Inspect Order

Inspect in this order unless the user request clearly narrows the scope:

1. Module families under `custom_addons/` and adjacent shared code.
2. `__manifest__.py` files to locate dependency hotspots, donor stacks, and suspicious cross-family coupling.
3. Models and inheritance:
   `_name`, `_inherit`, mixins, overrides, compute methods, onchange hooks, and cross-module imports.
4. Views, actions, and menus:
   inherited XML views, `ir.actions.*`, `menuitem`, context, domains, and routing from click to model behavior.
5. Security:
   `ir.model.access.csv`, record rules, implied groups, and whether UI entry points are reachable for intended users.
6. Tests and upgrade patterns:
   existing `tests/`, data migrations, optional setup patterns, and whether the module already has a preferred validation path.

## Boundary Notes

Treat these distinctions as first-class, because they change what should be edited:

- `addons/` is upstream vendor code unless the user explicitly asks to modify it.
- `custom_addons/` is the main project-owned customization area.
- `custom_addons/om_account_accountant-19.0.1.0.3` is vendored third-party code unless the user explicitly targets it.
- `gov_*` modules are project-owned public-sector contextualization, but they are not foundations for `br_*`.
- `br_*` modules must remain clean and independent of `gov_*` in `depends[]`.
- `base_accounting_kit` and `dynamic_accounts_report` are donor stacks, not authoritative foundations.
- Presence does not imply ownership or correctness. Prefer the module that the manifests, inheritance graph, and routing actually make authoritative.

## Output Shape

Produce a concise map with these sections when helpful:

- Observed module map:
  identify the likely owning modules, related addons, and whether they are project-owned, vendor, or donor.
- Dependency hotspots:
  call out manifests, inherited models, shared mixins, cross-module imports, or XML inheritance points that make the area fragile.
- Routing and inheritance map:
  trace menus, actions, views, model inheritance, and method overrides that govern the user-facing path.
- Security surface:
  note ACLs, rules, and group gating that may block or expose the behavior.
- Architectural tensions:
  list ambiguity, duplication, donor-copy drift, or namespace conflicts.
- Recommended narrowest edit surface:
  name the smallest credible module, file type, and extension strategy for a later implementation step.

Distinguish clearly between evidence from code and inference. Use concrete file paths, XML IDs, model names, and dependency names when available.

## Guardrails

- Do not implement unless the user explicitly asks for changes.
- Do not dump raw directory listings without interpretation.
- Do not assume a module is authoritative just because it exists.
- Do not stop at manifest inspection when menus, views, or inherited models decide the real behavior.
- Do not flatten repo-specific boundaries:
  keep project-owned, vendor, vendored third-party, and donor-stack roles separate in the analysis.
