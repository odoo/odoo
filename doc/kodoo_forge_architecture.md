# Kodoo Forge Architecture Note

Date: 2026-03-29

Objective:
- establish the first backend-first foundation for a Kodoo app-builder framework
- keep the canonical source of truth in a backend metamodel
- let UI be optional and replaceable
- support both managed runtime publication and real module export from the same source graph

## Observed Repo Fit

- Project-owned platform modules already live directly under `custom_addons`, for example `br_*`, `suite_dashboard_core`, and `kodoo_legal`.
- Domain-specific grouped families already have their own roots and addon paths:
  - `custom_addons/public_sector`
  - `custom_addons/knowledge`
- The local configs already include `custom_addons` in `addons_path`, so new root-level Kodoo modules work without config changes:
  - `deploy/odoo/kodoo.dev-host.conf.example`
  - `deploy/odoo/kodoo.dev-project.conf.example`
- There is already a vendor-style customization module in the repo, `custom_addons/app_odoo_customize-19.0.26.02.02/app_odoo_customize`, but its operating model is direct exposure of live runtime objects such as `ir.model`, `ir.model.fields`, `ir.ui.view`, and action/menu records. That is useful for admin customization, but it is the wrong architectural center for Kodoo Forge because it makes runtime objects the editing surface instead of keeping a canonical metamodel.

Recommendation:
- create Forge as a first-class Kodoo platform family directly under `custom_addons`
- do not place it under `public_sector` or `knowledge`
- do not build it on top of vendor customization modules

Initial location:
- `custom_addons/kodoo_forge`
- `custom_addons/kodoo_forge_runtime`
- `custom_addons/kodoo_forge_codegen`
- `custom_addons/kodoo_studio`

## Recommended Architecture

Kodoo Forge should have three planes:

### 1. Design Plane

Module:
- `kodoo_forge`

Responsibility:
- own the canonical metamodel
- validate blueprints
- snapshot immutable versions
- plan builds
- expose service methods for preview, publish, and export requests

This plane is the source of truth.

It must not depend on:
- OWL
- client action structure
- live edited `ir.model` or `ir.ui.view` records as canonical state

### 2. Materialization Plane

Modules:
- `kodoo_forge_runtime`
- `kodoo_forge_codegen`

Responsibility:
- consume a Forge snapshot or build plan
- produce a target representation

Two target strategies:
- runtime projection into managed Odoo metadata in the current database
- code generation into installable addon/module artifacts

Both targets must be fed from the same canonical snapshot graph.

### 3. Interaction Plane

Module:
- `kodoo_studio`

Responsibility:
- provide editing UX, preview UX, issue surfacing, and publish/export workflows
- call Forge services
- never become the schema owner

The UI may use OWL, but OWL is an adapter, not the architecture.

## Operating Model

Recommended lifecycle:

1. user edits a Forge draft graph
2. Forge validates and normalizes it
3. Forge freezes a snapshot
4. a build record is created from that snapshot
5. build target is chosen:
   - preview runtime
   - publish runtime
   - export code
6. materialization layer produces artifacts and records bindings

Key rule:
- generated runtime objects are managed outputs, never the canonical state

## Initial Module Split

### `kodoo_forge`

Owns:
- canonical metamodel models
- graph normalization
- validation rules
- snapshot storage
- build intents and orchestration
- internal binding abstraction contract

Does not own:
- direct runtime writes to `ir.model`, `ir.ui.view`, `ir.actions.*`, `ir.ui.menu`, `res.groups`, `ir.rule`
- frontend assets
- file export rendering

### `kodoo_forge_runtime`

Owns:
- managed runtime projection
- preview and publish reconcilers
- ownership markers on generated records
- runtime binding registry
- drift detection between snapshot and projected runtime

Does not own:
- draft editing
- UI workflow
- filesystem export

### `kodoo_forge_codegen`

Owns:
- manifest rendering
- Python/XML/CSV scaffold generation
- zip or attachment export packaging
- generated module tree assembly

Does not own:
- runtime publication
- metamodel editing
- frontend UI

### `kodoo_studio`

Owns:
- client actions and OWL editor shell
- property panels and builders
- build/run/export controls
- preview entrypoints and issue display

Does not own:
- canonical schema
- publish logic
- export rendering rules

## Canonical Backend Metamodel

Recommended technical model names:

- `kodoo.forge.app`
- `kodoo.forge.module`
- `kodoo.forge.model`
- `kodoo.forge.field`
- `kodoo.forge.view`
- `kodoo.forge.menu`
- `kodoo.forge.action`
- `kodoo.forge.security.group`
- `kodoo.forge.access.rule`
- `kodoo.forge.automation`
- `kodoo.forge.build`
- `kodoo.forge.snapshot`

Recommended internal support models later:
- `kodoo.forge.binding`
- `kodoo.forge.validation.issue`
- `kodoo.forge.module.dependency`

### `kodoo.forge.app`

Purpose:
- top-level product/workspace container

Core fields:
- `name`
- `technical_key`
- `summary`
- `description`
- `state`: draft, preview_ready, published, archived
- `target_odoo_series`
- `default_license`
- `default_category`
- `snapshot_head_id`
- `last_build_id`

Relations:
- one app to many modules
- one app to many snapshots
- one app to many builds

Notes:
- app is the portfolio object
- module is the deployable unit
- phase 1 can enforce one primary module per app while keeping the schema multi-module-ready

### `kodoo.forge.module`

Purpose:
- deployable addon unit inside an app

Core fields:
- `app_id`
- `name`
- `technical_name`
- `summary`
- `category`
- `license`
- `application`
- `installable`
- `sequence`
- `icon`
- `depends_json` or dependency child records
- `external_dependencies_json`

Relations:
- one module to many models
- one module to many views
- one module to many menus
- one module to many actions
- one module to many security groups
- one module to many access rules
- one module to many automations

Notes:
- module metadata must be canonical here, not reverse-engineered from `__manifest__.py`

### `kodoo.forge.model`

Purpose:
- canonical business model definition

Core fields:
- `module_id`
- `name`
- `technical_name`
- `description`
- `model_kind`: model, abstract, transient
- `inherit_mode`: new, inherit, delegate
- `inherit_model_names_json`
- `rec_name`
- `order`
- `active`

Relations:
- one model to many fields
- one model to many views
- one model to many access rules
- one model to many automations

Notes:
- phase 1 should prefer new managed models
- inherited edits to upstream models should be constrained and explicitly tracked

### `kodoo.forge.field`

Purpose:
- canonical field definition

Core fields:
- `model_id`
- `name`
- `field_description`
- `field_type`
- `required`
- `readonly`
- `store`
- `index`
- `copied`
- `translate`
- `help`
- `default_kind`
- `default_value`
- `relation_model_name`
- `inverse_name`
- `selection_json`
- `ondelete`
- `compute_mode`: none, expression, manual
- `compute_expression`
- `widget_hint`

Notes:
- keep the field DSL backend-owned
- do not let runtime `ir.model.fields` become the authoring source
- `manual` compute mode is a handoff marker for codegen/manual extension, not something runtime should silently emulate

### `kodoo.forge.view`

Purpose:
- canonical UI definition for a model

Core fields:
- `module_id`
- `model_id`
- `name`
- `view_type`: list, form, search, kanban, calendar, graph, pivot, activity
- `mode`: primary, inherit
- `priority`
- `parent_view_key`
- `schema_json`
- `raw_arch_override`
- `generated_arch_cache`
- `active`

Notes:
- the canonical form should be `schema_json` or a normalized backend AST
- generated XML is a derivative cache
- the visual editor edits the schema, not `arch_db`

### `kodoo.forge.menu`

Purpose:
- canonical navigation tree

Core fields:
- `module_id`
- `name`
- `parent_id`
- `sequence`
- `action_id`
- `web_icon`
- `group_ids`
- `active`

### `kodoo.forge.action`

Purpose:
- canonical user-facing action definition

Core fields:
- `module_id`
- `name`
- `action_type`: act_window, server, url, client, report
- `model_id`
- `view_mode`
- `view_ids`
- `domain_json`
- `context_json`
- `target`
- `binding_model_name`
- `help_html`
- `payload_json`

Notes:
- phase 1 should focus on `act_window`
- other action types should be modeled now but may stay out of MVP materialization

### `kodoo.forge.security.group`

Purpose:
- canonical security role definition

Core fields:
- `module_id`
- `name`
- `technical_name`
- `category_name`
- `comment`
- `implied_group_keys_json`

### `kodoo.forge.access.rule`

Purpose:
- unified canonical representation for ACLs and record rules

Core fields:
- `module_id`
- `model_id`
- `name`
- `rule_kind`: acl, record
- `group_ids`
- `perm_read`
- `perm_write`
- `perm_create`
- `perm_unlink`
- `domain_expression`
- `active`

Notes:
- for ACL records, `domain_expression` is empty
- for record rules, CRUD flags and domain are both meaningful

### `kodoo.forge.automation`

Purpose:
- canonical automation definition

Core fields:
- `module_id`
- `model_id`
- `name`
- `automation_type`: record_event, scheduled, manual, webhook
- `trigger_events_json`
- `trigger_domain`
- `step_schema_json`
- `sequence`
- `active`

Notes:
- keep automation steps in a backend schema
- do not start with arbitrary Python snippets in the metamodel

### `kodoo.forge.build`

Purpose:
- immutable build attempt against a snapshot

Core fields:
- `app_id`
- `snapshot_id`
- `build_type`: preview, publish, export
- `target_kind`: runtime, code
- `status`: draft, queued, running, failed, done, cancelled
- `requested_by`
- `requested_at`
- `started_at`
- `finished_at`
- `diff_summary_json`
- `log_text`
- `artifact_attachment_id`
- `runtime_revision`

Notes:
- builds are execution records, not drafts
- every materialization should happen through a build

### `kodoo.forge.snapshot`

Purpose:
- immutable frozen copy of the blueprint graph

Core fields:
- `app_id`
- `label`
- `version`
- `parent_snapshot_id`
- `source_build_id`
- `graph_json`
- `content_hash`
- `notes`
- `created_by`
- `created_at`

Notes:
- export and publish should consume snapshots
- a snapshot is the point where runtime and codegen stay aligned

## Boundary: Runtime Generation vs Code Export vs Manual Extension

### Purely Declarative Runtime Generation

This should stay safe, idempotent, and reversible.

Belongs here:
- managed creation of new business models
- supported field types:
  - char
  - text
  - html
  - integer
  - float
  - monetary
  - boolean
  - date
  - datetime
  - selection
  - many2one
- generated list, form, and search views
- generated window actions and menus
- security groups
- ACLs and simple record rules
- safe automation recipes from a supported DSL
- preview and publish of managed runtime objects

Should not be phase 1 runtime generation:
- arbitrary Python compute code
- arbitrary Python constraints or onchange logic
- custom controllers
- custom reports
- custom JS widgets
- website page builders
- raw SQL and migration logic

### Code Generation / Export

Belongs here:
- `__manifest__.py`
- Python model files and module packages
- view XML files
- action/menu XML files
- security CSV/XML
- data XML files
- zip or attachment artifact assembly
- extension stubs for later manual work

This is the path for:
- source control
- CI
- shipping installable modules across databases
- long-term maintainability when apps outgrow purely declarative runtime

### Advanced / Manual Developer Extension

Belongs here:
- complex compute methods
- custom business services
- controllers and APIs
- OWL widgets and bespoke frontend components
- reports and exports outside the declarative renderer
- performance tuning and indexes
- advanced integrations
- test suites beyond generated smoke coverage

Recommended pattern:
- generated module remains the canonical exported base
- a hand-written companion module, for example `<module>_ext`, adds bespoke behavior
- Forge should model the need for manual extension instead of trying to absorb all custom code into its own DSL

## Phase 1 MVP Scope

Recommended MVP:

- one app with one primary module
- new managed models only
- supported fields:
  - char
  - text
  - integer
  - float
  - boolean
  - date
  - datetime
  - selection
  - many2one
- generated views:
  - list
  - form
  - search
- generated navigation:
  - window actions
  - menus
- generated security:
  - groups
  - ACLs
  - simple record rules
- snapshots
- build records
- preview publish into managed runtime bindings for builder users
- export of a zip artifact containing an installable module tree
- a minimal Studio shell focused on structured editing, not full drag-and-drop

Explicitly out of MVP:
- editing upstream model internals freely
- arbitrary `arch_db` editing as the primary editor
- Python snippets in automations
- reports
- website builders
- JS widget authoring
- multi-module cross-app orchestration

## Dependency Recommendation

Recommended hard dependencies:

- `kodoo_forge`
  - depends: `base`
- `kodoo_forge_runtime`
  - depends: `kodoo_forge`
- `kodoo_forge_codegen`
  - depends: `kodoo_forge`
- `kodoo_studio`
  - depends: `kodoo_forge_runtime`, `web`

Recommended optional bridge modules later instead of bloating the core:

- `kodoo_forge_automation`
  - depends: `kodoo_forge_runtime`, `base_automation`
- `kodoo_forge_mail`
  - depends: `kodoo_forge_runtime`, `mail`
- `kodoo_forge_website`
  - depends: `kodoo_forge_runtime`, `website`

Reason:
- keep Forge core generic and lean
- keep runtime/export parity centralized
- isolate Odoo-surface-specific features behind bridges

## Main Risks

### 1. Runtime Drift

If generated Odoo runtime records are manually edited after publication, the blueprint and runtime diverge.

Mitigation:
- ownership markers
- binding registry
- drift checks before publish
- published objects treated as generated outputs

### 2. UI-Centric Schema Creep

If the Studio editor becomes the de facto schema, backend independence is lost.

Mitigation:
- backend AST/JSON schema as canonical
- UI works as a projection/editor only

### 3. Runtime and Export Parity Split

If runtime projection and file export use different rendering assumptions, the same app behaves differently depending on target.

Mitigation:
- both targets consume the same snapshot
- shared normalization layer
- shared renderer contracts

### 4. Overreaching DSL

Trying to encode all Python-level behavior into Forge too early will make the system brittle.

Mitigation:
- keep phase 1 declarative
- introduce explicit handoff to manual extension modules

### 5. Unsafe Structural Changes

Renames, deletions, or field-type changes can corrupt runtime data or break published apps.

Mitigation:
- snapshot diffs
- guarded migration policies
- explicit destructive-change review in builds

## Proposed Initial Directory and File Skeleton

Recommended first real skeleton:

```text
custom_addons/
  kodoo_forge/
    __init__.py
    __manifest__.py
    README.md
    models/
      __init__.py
    services/
      __init__.py
    security/
    views/
    tests/
      __init__.py
  kodoo_forge_runtime/
    __init__.py
    __manifest__.py
    README.md
    services/
      __init__.py
    views/
    tests/
      __init__.py
  kodoo_forge_codegen/
    __init__.py
    __manifest__.py
    README.md
    services/
      __init__.py
    views/
    tests/
      __init__.py
  kodoo_studio/
    __init__.py
    __manifest__.py
    README.md
    static/
      src/
        js/
        xml/
        scss/
    views/
    tests/
      __init__.py
```

Next files to add after this skeleton:

- `kodoo_forge/models/forge_app.py`
- `kodoo_forge/models/forge_module.py`
- `kodoo_forge/models/forge_model.py`
- `kodoo_forge/models/forge_field.py`
- `kodoo_forge/models/forge_view.py`
- `kodoo_forge/models/forge_menu.py`
- `kodoo_forge/models/forge_action.py`
- `kodoo_forge/models/forge_security.py`
- `kodoo_forge/models/forge_automation.py`
- `kodoo_forge/models/forge_build.py`
- `kodoo_forge/models/forge_snapshot.py`
- `kodoo_forge/services/validation_service.py`
- `kodoo_forge/services/snapshot_service.py`
- `kodoo_forge/services/build_service.py`
- `kodoo_forge_runtime/services/runtime_projector.py`
- `kodoo_forge_runtime/services/runtime_binding_service.py`
- `kodoo_forge_codegen/services/addon_export_service.py`
- `kodoo_studio/views/kodoo_studio_actions.xml`
- `kodoo_studio/static/src/js/kodoo_studio_app.js`
- `kodoo_studio/static/src/xml/kodoo_studio_app.xml`

## Bottom Line

Recommended foundation:
- backend-first metamodel in `kodoo_forge`
- separate runtime materialization in `kodoo_forge_runtime`
- separate source export in `kodoo_forge_codegen`
- UI in `kodoo_studio`

Recommended repo placement:
- direct root-level `custom_addons/kodoo_*` modules

Recommended phase 1 posture:
- structured schema editor
- safe declarative runtime
- snapshot/build/export pipeline
- no attempt to replace handwritten Odoo development for advanced behavior
