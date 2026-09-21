.. _coding_guidelines:

===========================
AgroMarin Coding Guidelines
===========================

:Version: 6.58
:Date: 2026-09-16
:Base: `Odoo 19.0 Coding Guidelines <https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html>`_
       + `OCA CONTRIBUTING.rst <https://github.com/OCA/odoo-community.org/blob/master/website/Contribution/CONTRIBUTING.rst>`_

The coding standard for the AgroMarin fork of Odoo 19.0. Authoritative where it
speaks; where silent, follow upstream Odoo 19, then OCA. Fix a stale claim in the
same PR as the code that made it stale.

.. contents::
   :local:
   :depth: 2

----

How rules are enforced
======================

Each rule carries a bracketed label naming what catches it.

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Label
     - Meaning
   * - ``[ruff CODE]``
     - ``ruff check`` reports it.
   * - ``[test_lint CODE]``
     - A ``test_lint`` rule fails on it. ``E8501``--``E8530`` are the Python
       AST checkers; the XML rules are named by rule (``data-root``,
       ``duplicate-field``, ...) and every other ``test_lint`` gate by test.
   * - ``[fixer NAME]``
     - A behaviour-preserving fixer owns the formatting. Run it; do not hand-edit.
   * - ``[ratchet NAME]``
     - A ``test_lint`` floor in ``odoo/addons/test_lint/tests/floors.json``
       holds the count; with no entry, the count is held at zero. Every other
       ratchet went with ``tooling/`` on 2026-09-11 and the label now reads as
       ``[review]``.
   * - ``[gate NAME]``
     - A ``tooling/`` gate checked it exactly, both directions, until
       ``tooling/`` was removed on 2026-09-11. Read as ``[review]``; the
       figures such a gate rewrote (the census table below among them) are as
       of the day they were last regenerated.
   * - ``[review]``
     - No tool checks this. A human does, using §9.

Do not infer enforcement from phrasing: several rules that read like lint rules
are ``[review]`` because the ``ruff`` code is disabled with a rationale in
``ruff.toml``.

The floors
----------

Until 2026-09-11 every countable gate was a *ratchet*: a total measured against
a committed floor in ``tooling/ratchet/baselines/``, held exactly in both
directions by ``ratchet.py``. That tree -- 84 floors, the architecture gates,
the naming vocabulary, the length and complexity counts, the sibling-repo lint
runner -- is deleted. What remains countable is held as follows:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Gate
     - Command
     - Held at
   * - ruff
     - ``ruff check odoo/ --no-cache --statistics``
     - ``odoo/`` only -- a **hard zero**
   * - ruff (tests)
     - ``ruff check tests/ --no-cache`` and ``ruff format --check tests/``
     - a **hard zero**
   * - mypy
     - ``mypy -p odoo.orm -p odoo.db -p odoo.libs -p odoo.http -p odoo.service -p odoo.modules``
     - typed packages; last banked at zero. Measure with mypy alone installed,
       never in the workspace venv, whose stubs move the count
   * - ESLint
     - ``npx eslint .``
     - every JS/MJS the config does not ignore -- a **hard zero**
   * - ``tsc``
     - ``npx tsc --project tsconfig.json --noEmit``
     - all checked JS; last banked at zero
   * - prettier (SCSS)
     - ``npx prettier --list-different "**/*.scss"``
     - last banked at zero
   * - ``test_lint``
     - ``odoo-bin -i test_lint --test-enable --test-tags /test_lint``
     - ``odoo/addons/test_lint/tests/floors.json``, one integer per gate, exact
       in both directions

There is no tool to move a ``test_lint`` floor: edit the JSON in the same change
that moves the count. A gate with no entry is a hard zero.

Consequences:

* **``ruff`` measures ``odoo/``, not ``addons/``.** For addons, ``ruff`` is
  pre-commit and review discipline.
* **A finding on a file you touched may predate you.** Compare against
  ``git diff``, not a whole-file lint report.
* **``ruff`` is a hard zero over the whole selected ruleset.** ``ruff.toml``
  ignores ``C901`` to keep complexity out of the aggregate;
  ``ruff check odoo/ --select C901`` re-selects it, and raising
  ``[lint.mccabe] max-complexity`` lowers that count without fixing anything.
* **The architecture contracts are review rules now.** Layer crossings, the
  façade boundary and import cycles were held at zero by ``layer_check.py``,
  ``py_cycle_check.py`` and ``js_cycle_check.py``; ``doc/architecture/module.md``
  still states the legal directions and nothing checks them.

Nothing runs any of this on a schedule; there is no CI.

The ``test_lint`` module
------------------------

``odoo/addons/test_lint`` holds AST checkers and registry-level tests encoding
Odoo-specific rules no general linter knows. **Every rule is an exact-match
ratchet** (``LintCase.assert_ratchet``, floors in ``tests/floors.json`` beside
it): the count may not rise, and may not fall silently. No
rule is advisory and none fails outright -- the floor is what decides.

Two scopes. Installing ``base`` + ``test_lint`` and running ``/test_lint``
covers the AST rules, which scan the whole tree; the classes needing a real
registry (bundles, dark siblings, ESM specifiers) need a fuller install.

**Harvest a floor at the narrow scope**, ``--addons-path=odoo/addons,addons`` with
only ``test_lint`` installed. A gate reading the installed registry measures a
different tree on a fuller install, and a floor taken there cannot pass at the
narrow scope:

.. code-block:: bash

   odoo-bin --addons-path=odoo/addons,addons -d <db> -i test_lint \
       --test-enable --test-tags /test_lint --stop-after-init --no-http

The AST rules. ``_rules.RULES`` is the registry; ``_py_scan`` is the engine.

.. list-table::
   :header-rows: 1
   :widths: 30 10 60

   * - Rule
     - Code
     - Catches
   * - ``sql-injection``
     - ``E8501``
     - Dynamic SQL built by interpolation (§10.4)
   * - ``gettext-variable``
     - ``E8502``
     - ``_()`` called with a non-literal first argument (§8.1)
   * - ``gettext-placeholders``
     - ``E8503``
     - Two or more *unnamed* placeholders in a translated string (§8.1)
   * - ``gettext-repr``
     - ``E8504``
     - ``%r`` inside a translated string (§8.1)
   * - ``missing-gettext``
     - ``E8505``
     - Raw string literal passed to a user-facing exception (§2.7)
   * - ``raise-unlink-override``
     - ``E8506``
     - ``raise`` inside an ``unlink()`` override (§2.6)
   * - ``n-plus-one-query``
     - ``E8507``
     - Query call inside a ``for`` loop (§11.1)
   * - ``orm-import``
     - ``E8508``
     - Addon runtime code importing ``odoo.orm`` directly (§2.1)
   * - ``onchange-domain``
     - ``E8509``
     - Domain returned from an ``@api.onchange`` (§2.9.9)
   * - ``config-chainmap-patch``
     - ``E8510``
     - ``patch.dict`` over the config options ChainMap -- it flattens every
       lower layer into ``_override_options`` and the damage lands on the next
       test. Use ``config.patch(**values)``
   * - ``gettext-developer-error``
     - ``E8511``
     - ``_()`` around a builtin exception's message: a traceback is not
       user-facing, and translating it books a diagnostic into the catalogue
   * - ``unique-over-translated-column``
     - ``E8512``
     - ``UNIQUE`` declared over a ``translate=True`` column (§2.9.8)
   * - ``shadowed-definition``
     - ``E8513``
     - A class body defining the same member twice; Python silently keeps the
       last
   * - ``tax-company-singular``
     - ``E8514``
     - ``t.company_id`` inside a ``filtered`` lambda over a tax field;
       ``account.tax`` carries ``company_ids``
   * - ``http-json-string``
     - ``E8515``
     - ``return json.dumps(...)`` from a ``type="http"`` route: the JSON goes
       out as ``text/html`` and the client's ``post()``/``get()`` refuse it;
       return ``request.prepare_json_response(payload)``
   * - ``noqa-rationale``
     - --
     - ``# noqa`` without a written rationale (§*Suppressing a rule*)
   * - ``unreadable-source``
     - --
     - A file the scan cannot parse, so every other rule skipped it in silence

``noqa-rationale`` and ``unreadable-source`` are unsuppressable, and the second
is held at zero rather than ratcheted.

The registry and tree gates carry no code and are named by test.

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Test
     - Rule
   * - ``test_index``
     - Stored One2many inverse not indexed (§11.5)
   * - ``test_naming``
     - Public method with an ``ids`` or ``context`` parameter (§2.4.15)
   * - ``test_override_signatures``
     - Override whose signature diverges from its parent (§2.4.15)
   * - ``test_manifests``
     - ``__manifest__.py`` the fixer would rewrite (``lint_manifest_shape``),
       or a value it cannot decide -- unknown key, wrong type, missing file,
       unresolvable dependency, unbound hook (``lint_manifest_value``) (§1.2)
   * - ``test_test_holes``
     - Test file not imported exactly once in ``tests/__init__.py`` (§6.1)
   * - ``test_docstring``
     - Docstring fields disagreeing with the signature (§2.5)
   * - ``test_routes``
     - Inherited route restating an unchanged attribute (§2.8)
   * - ``test_l10n``
     - Mis-tagged localisation test (§6.7)
   * - ``test_group_refs``
     - ``groups=`` naming a group the module never defines (§10.8)
   * - ``test_xml_records`` / ``test_pretty_xml``
     - ``<field>`` child order, attribute order, XML formatting (§3.1)
   * - ``test_view_hygiene`` / ``test_menu_parents``
     - View-attribute vocabulary, kanban template scope, a group-by filter
       carrying a domain, orphan labels, ``act_window`` view order, a
       ``menuitem`` whose parent no module defines
   * - ``test_esm_specifiers`` / ``test_esm_bundles``
     - Unresolvable ``@addon/…`` import; ES-module bundle undeclared (§4.1)
   * - ``test_scheme_duplication`` / ``test_dark_sibling_scope``
     - Rules restated per colour scheme; dark-sibling placement (§5.3, §5.5)
   * - ``test_asset_paths_exist`` / ``test_bundles_assemble``
     - An ``assets`` glob matching no file; a bundle that does not assemble
   * - ``test_pofile``
     - Duplicate entries in a ``.pot`` file (§8.3)
   * - ``test_i18n`` / ``test_jstranslate``
     - Untranslatable static strings in templates and JS (§8.2)
   * - ``test_dunderinit`` / ``test_markers``
     - Module without an ``__init__.py``; conflict markers or NUL bytes
   * - ``test_pep649``
     - Annotations that fail to resolve under PEP 649

``test_docstring`` and ``TestSchemeDuplication`` read the installed registry, so
the narrow scope cannot grade them: the first measures 1 there against 32 on a
fuller install, and the second **skips** rather than passing. Grade them on a
fuller install.


Suppressing a rule
------------------

Every suppression states why ``[test_lint]``:

.. code-block:: python

   value = compute()  # noqa: RUF015 — ordering is guaranteed by the caller

Bare ``# noqa``, or ``# noqa: CODE`` with nothing after it, is itself a
violation; the rationale needs at least four non-space characters including a
letter. For the ``E85xx`` checkers, ``# noqa: E8501`` and
``# pylint: disable=sql-injection`` are both recognised. Broader escapes --
``ruff.toml`` ``per-file-ignores``, the allow-lists in ``test_index.py`` and
``test_override_signatures.py`` -- are config changes needing review on their own
merits.

Quick Reference
===============

**Python**

* Double quotes, line length 88; match ``ruff format``'s output in what you
  write, never reformat a whole inherited file (§2.1).
* One model per file, named after ``_name`` (§1.3) ``[review]``.
* Reach the ORM through ``odoo.api`` / ``odoo.fields`` / ``odoo.models``, never
  ``odoo.orm`` from addon runtime code (§2.1) ``[test_lint]``.
* Every model declares ``_name`` and ``_description`` (§2.6) ``[review]``.
* Override ``create`` as ``@api.model_create_multi def create(self, vals_list)``;
  always ``super()`` in ``create`` / ``write`` / ``unlink`` / ``copy_data`` /
  ``default_get`` (§2.6) ``[review]``.
* Deletion constraints use ``@api.ondelete``; ``raise`` inside an ``unlink``
  override is a violation (§2.6) ``[test_lint E8506]``.
* Name new buttons ``action_*``; never rename an inherited core method (§2.4).
* One verb per operation: ``_prepare_`` builds payloads, ``_get_`` reads,
  ``_check_`` raises, ``_is_``/``_has_``/``_can_`` return booleans, ``_update_``
  writes, ``_add_``/``_remove_`` for collections. ``_build_``, ``_fetch_``,
  ``_validate_``, ``_verify_``, ``_ensure_``, ``_do_``, ``_run_``, ``_perform_``
  are abolished (§2.4) ``[review]``.
* ``odoo.fields.Command`` for x2many writes, never raw tuples (§2.9.7)
  ``[review]``.
* Never compare money or floats with ``==`` / ``!=`` / ``<`` / ``>`` -- use
  ``float_compare`` / ``float_is_zero`` (§2.9.12). Only ``==`` / ``!=`` is linted
  ``[ruff RUF069]``.
* User-facing text goes through ``self.env._(...)`` with ``%s`` arguments (§8.1)
  ``[test_lint E8502]``.
* ``raise X from Y`` inside ``except`` (§2.7) ``[ruff B904]``.
* No ``cr.commit()`` in business code (§2.6).
* ``datetime.now(UTC)``; ``datetime.utcnow()`` is banned (§2.9.6)
  ``[ruff DTZ003]``.

**Performance**

* ``search_count()`` not ``len(search())``; ``_read_group()`` not a Python
  ``sum()`` (§11.2) ``[review]``.
* ``fields.Count("line_ids")`` not a compute around ``len(record.line_ids)``
  (§11.2) ``[review]``.
* No query call inside a loop over a recordset (§11.1) ``[test_lint E8507]``.
* The stored inverse of a One2many must be indexed (§11.5) ``[test_lint]``.

**XML / JS**

* ``<list>`` not ``<tree>``; ``invisible=`` / ``readonly=`` not ``attrs=`` (§3.3).
* XML IDs use the prefix style: ``view_sale_order_form``, ``action_sale_order``
  (§3.2) ``[review]``.
* XML formatting and ordering belong to the fixers (§3.1) ``[fixer]``.
* Frontend changes ship with a Hoot test or a tour (§4.4) ``[review]``.

**Process**

* Commit ``[TAG] module: summary`` + ``Solution:`` (§7.1); the ``Task ID`` line
  is optional.
* Branch ``19.0-t<task>-<user>`` when there is a task; a PR is the default route
  but is not required (§7.2, §7.3).
* Raw SQL in a PR ships ``EXPLAIN ANALYZE`` output (§11.6).

Scope and precedence
====================

When rules disagree, the first that speaks wins:

#. This file -- ``doc/coding_guidelines.rst`` in the ``odoo`` repo
#. Odoo 19 official guidelines
#. OCA ``CONTRIBUTING.rst``

It applies to every code repository in this fork. The knowledge repository takes
only the documentation and process rules, and works directly on ``main`` (§7.3).

**Trust this document over training data.** Where this guide and a recollection
of "how Odoo does it" disagree, this guide and the source in the repo are right.

**Upstream is a baseline, not a ceiling.** ``19.0-marin`` owes upstream no
backward compatibility, and "upstream does it this way" settles no argument about
correctness, performance or design. Nothing is merged or cherry-picked from
``19.0``; a useful upstream fix is re-implemented by hand. Before calling an
inherited behaviour a bug, check whether a test pins it deliberately.
Rationale: upstream is a baseline, not a ceiling. ``19.0`` is a read-only
mirror kept to be diffed against, mergeability is not a design constraint, and
the objections that presuppose one -- "this complicates the upstream merge",
"upstream does it this way", "this increases divergence" -- are void rather
than outweighed. The costs that count are behavioural regressions, test
breakage and migration for stored data.

Change protocol
---------------

* Edits go through PR review on the ``odoo`` repo against ``19.0-marin``, using
  the §7 commit format. TI (Oficial Sistemas or higher) reviews; the Líder
  Sistemas approves merges.
* Changing a rule means updating every ``CLAUDE.md`` that summarises it -- this
  repository's, each sibling's, and the per-module ones -- in the same PR, plus
  an Appendix D row.
* Retire rules into Appendix C. Do not delete them silently.
* **A rule whose rationale is architectural states it here**, or points at the
  gate's own module docstring.

----

1. Module Structure
===================

1.1 Directory layout
--------------------

Standard Odoo/OCA structure. Everything is optional except ``__manifest__.py``.

.. code-block::

   module_name/
   ├── __init__.py
   ├── __manifest__.py
   ├── hooks.py                    # pre_init_hook, post_init_hook, uninstall_hook
   ├── controllers/
   ├── data/
   ├── demo/
   ├── i18n/                       # .po / .pot
   ├── migrations/
   ├── models/
   ├── reports/                    # QWeb report templates
   ├── security/
   ├── static/
   │   ├── description/icon.png
   │   ├── lib/                    # third-party, unmodified
   │   └── src/
   ├── tests/
   ├── views/
   └── wizards/                    # TransientModel, incl. res.config.settings

**The directory names are plural** ``[review]``: ``wizards/`` and ``reports/``,
never ``wizard/`` or ``report/``. Upstream spells both in the singular, and so
did most of this tree until 2026-09-11, when every one of the 328 ``wizard/``
and 182 ``report/`` directories across ``odoo``, ``enterprise`` and
``agromarin`` was renamed in one pass; a singular directory is a regression
now, not debt. Renaming one is a rename of every path in ``__manifest__.py``,
of the package import in the module's ``__init__.py`` and of every dotted
``odoo.addons.<module>.wizard`` import elsewhere; do it as one change with all
three. Nothing else reads the name: ``naming_vocabulary.py`` governs *any*
file under a manifest (§2.4.13), so the singular is not shielded from a gate
and the plural is not exposed to one.

Under ``static/src``, colocate a component's ``.js``, ``.xml`` and ``.scss`` in a
feature folder. The flat ``js/`` + ``xml/`` + ``scss/`` split is legacy (§4.1).

1.2 ``__manifest__.py``
-----------------------

Keys come from the known set, in the canonical order
``[test_lint lint_manifest_shape]``; the fixer owns the shape
``[fixer _sort_manifests]`` and the vocabulary is its ``MANIFEST_KEY_ORDER``:

``name``, ``version``, ``category``, ``sequence``, ``summary``, ``description``,
``author``, ``contributors``, ``maintainer``, ``maintainers``, ``website``,
``url``, ``support``, ``live_test_url``, ``price``, ``currency``, ``icon``,
``images``, ``images_preview_theme``, ``license``, ``depends``,
``external_dependencies``, ``countries``, ``data``, ``demo``,
``oca_data_manual``, ``assets``, ``esm``, ``bootstrap``, ``web``,
``configurator_snippets``, ``configurator_snippets_addons``,
``new_page_templates``, ``theme_customizations``, ``iot_handlers_in_image``,
``cloc_exclude``, ``installable``, ``application``, ``auto_install``,
``post_load``, ``pre_init_hook``, ``post_init_hook``, ``uninstall_hook``.

``init_xml``, ``update_xml``, ``demo_xml`` and ``test`` are deprecated: the
loader defaults them and nothing reads them ``[test_lint lint_manifest_value]``.

**The fixer normalises, and the shape gate reads "the fixer would rewrite
it".** What it changes is loader-neutral or a rule of this section: a key
restating its ``_DEFAULT_MANIFEST`` value is dropped (``installable: True``,
``application: False``, ``auto_install: False``, ``data: []``, ``sequence:
100`` -- ``version`` is kept, and ``auto_install: []`` is not the default, it
means *always*); ``name``, ``category``, ``author``, ``license`` and the URL
keys are stripped; ``summary`` is one line; a whitespace-only ``description``
or ``website`` is dropped (a whitespace ``description`` is truthy, so it
*blocks* the README fallback); ``countries`` is lowercase; an ``icon`` equal to
``/<module>/static/description/icon.png`` is dropped; a ``set`` under
``assets`` becomes a sorted list. Strings are written as they are, never
``\uXXXX``-escaped.

**What the fixer cannot decide is a value finding** ``[test_lint
lint_manifest_value]``: an unknown key; a wrong type; a ``version`` the loader
would mark uninstallable; a ``license`` outside ``ir.module.module``'s
selection; a ``category`` with an empty segment or a root no
``ir_module_category_data.xml`` declares; a URL key without a scheme;
``depends`` naming itself, a duplicate, or a module on no addons path; an
``auto_install`` trigger outside ``depends``; ``external_dependencies`` with a
kind other than ``python``, ``bin``, ``apt``, or an ``apt`` hint for a
dependency ``python`` does not declare; a ``countries`` code that is not two
letters, or one country with no ``l10n`` in the module name; a ``data`` or
``demo`` entry matching no file or listed twice, a ``demo`` entry outside
``demo/``, a ``data`` entry under ``demo/`` or named ``*_demo``; an ``icon``
matching no file; a hook ``__init__.py`` does not bind; an ``assets`` bundle
not ``<module>.<bundle>``, not a list, or carrying a directive the asset
pipeline does not know. Both gates read only this checkout; the sibling
repositories run the same two scripts by hand, from the workspace root::

   p314o19m/bin/python odoo/odoo/addons/test_lint/tests/_sort_manifests.py --dry-run enterprise agromarin design-themes
   p314o19m/bin/python odoo/odoo/addons/test_lint/tests/_checker_manifest.py odoo/odoo/addons odoo/addons enterprise agromarin design-themes

.. code-block:: python

   {
       "name": "Module Name",
       "version": "19.0.1.0.0",
       "category": "Sales",
       "author": "AgroMarin",
       "license": "LGPL-3",
       "depends": ["sale"],
       "data": [
           "security/ir.model.access.csv",
           "views/sale_order_views.xml",
       ],
   }

* **Version**: ``{odoo_version}.x.y.z`` -- *x* breaking, *y* feature, *z* fix.
* **Omit empty keys.**
* **``depends`` lists direct dependencies only**, never transitive ones.
* **``auto_install``** only for a genuine bridge module between two independent
  modules, as ``sale_crm`` bridges ``sale`` and ``crm``.
* **A mixin is not a module by default.** One that depends on ``base`` alone
  and ships no data lives in ``base``; §2.2.2 says what earns one a module.
* **Demo data belongs in ``demo``, not ``data`` -- the key and the directory
  both** ``[review]``. A file listed under ``demo`` lives in ``demo/``; a
  ``data/{model_name}_demo.xml`` is a demo file filed as data, and the manifest
  key alone does not correct it. Upstream mixes the two, and so did this tree
  until 2026-09-11, when the 331 ``demo`` entries (of 726 across ``odoo``,
  ``enterprise`` and ``agromarin``) that pointed into ``data/`` were moved in
  one pass; a demo file under ``data/`` is a regression now. Move the file and
  the manifest entry together, and follow any code that loads the file by
  path -- ``convert_file`` in an onboarding action is the usual one. A demo
  file is loaded only when the database has demo data, so the move changes
  what a fresh install without it loads not at all. **A file listed under both
  keys is a data file**: drop the ``demo`` entry rather than move it.
* **Demo data reaches a workflow state through the workflow** ``[review]``. A
  record whose ``state`` the model computes from decisions is created in its
  initial state and driven by a ``<function>`` calling the same actions a user
  would -- ``approval``'s demo confirms, approves, refuses and cancels its
  requests through ``_load_demo_workflow`` -- never by writing ``state``,
  ``date_confirmed`` or a refusal into the record. A model that guards those
  fields refuses the forged record; one that does not gets a record no
  transition produced, with every side effect (approver rows, activities,
  chatter, dates) missing. The same rule as a test that reaches a state.
* **A demo file must load** ``[review]``. The loader catches a failing demo
  file, logs *installed without demo data* and carries on, so a broken one is
  red in no lane anyone runs. Measured 2026-09-11 with ``--with-demo`` over
  every module that ships a ``demo`` key: nine files named a field this fork
  had renamed (``product_uom_qty``, ``date_planned``, ``deadline``,
  ``product_category_id``), one forged a workflow state, one duplicated a
  unique key, one carried an invalid VAT. Load your demo data before landing
  it, on a server with nothing in its environment: a demo or data file
  never stores a secret (``credential.credential`` exists unprovisioned
  until one is entered, and a ``post_init_hook`` that generates one checks
  ``_is_encryption_key_configured()`` first), because a file that needs
  ``ODOO_API_ENCRYPTION_KEY`` fails on every server that lacks it.
* **``license``** must match how the module is actually distributed. The fork
  ships ``LGPL-3``, ``OPL-1``, ``AGPL-3`` and ``OEEL-1``; do not copy a
  neighbour's value unchecked.

**External dependencies** go in the manifest *and* in the requirements file of
the repo owning the module -- ``requirements-addons.txt`` here,
``requirements.txt`` in the sibling addon repositories, never
``odoo/requirements.txt``, which carries only what the framework and
always-loaded addons import.

.. code-block:: python

   "external_dependencies": {"python": ["requests"], "bin": ["wkhtmltopdf"]},

* Use the **PyPI distribution name**, not the import name (``python-ldap``, not
  ``ldap``): ``check_python_external_dependency`` resolves it through
  ``importlib.metadata.version`` and falls back to importing the name only after
  logging a warning.
* **Declare only what the module cannot start without.** A dependency behind a
  ``find_spec`` guard, a function-local import or ``try/except ImportError`` is
  optional by construction, and declaring it converts a degrading feature into a
  refused install. ``base_import`` declares ``chardet`` and deliberately not
  ``xlrd``, ``odfpy`` or ``openpyxl``.
* **An ``auto_install`` module cannot rely on the declaration.**
  ``odoo/modules/db.py`` marks the auto-install closure in raw SQL and never
  consults ``external_dependencies``, which is checked on the UI install path
  only -- pin the dependency as a server requirement instead. ``cbor2``
  (``auth_passkey``) and ``ofxparse`` (``account_bank_statement_import_ofx``) are
  the two such cases.

1.3 File naming
---------------

**One model per file** ``[review]``. A ``.py`` under ``models/`` (or
``wizards/``) declares exactly one model class -- one ``models.Model``,
``models.AbstractModel`` or ``models.TransientModel`` -- named after that model's
``_name`` with dots as underscores. A second model class is a second file,
whatever its size; ``models/__init__.py`` imports them in dependency order. The
rule holds for extensions: fields added to ``sale.order`` under ``_inherit`` go in
the module's own ``models/sale_order.py``.

Adoption is partial. Apply the rule to files you create or substantially rework.

.. list-table::
   :header-rows: 1

   * - Type
     - Pattern
     - Example
   * - Model
     - ``models/{model_name}.py``
     - ``sale_order.py`` for ``sale.order``
   * - Mixin
     - ``models/{model_name}.py``
     - ``mixin_mail_activity.py`` for ``mixin.mail.activity`` (§2.2.1)
   * - Views
     - ``views/{model_name}_views.xml``
     - ``sale_order_views.xml``
   * - Data
     - ``data/{model_name}_data.xml``
     - ``sale_order_data.xml``
   * - Demo
     - ``demo/{model_name}_demo.xml``
     - ``sale_order_demo.xml``; listed under ``demo`` in the manifest and never
       filed under ``data/`` (§1.2)
   * - Menus
     - ``views/ir_ui_menu_views.xml``
     - one file, every menuitem
   * - Access rights
     - ``security/ir.model.access.csv``
     - always CSV
   * - Groups
     - ``security/res_groups.xml``
     -
   * - Record rules
     - ``security/ir_rule.xml``
     - every ``ir.rule`` in one file
   * - Wizards
     - ``wizards/{model_name}.py`` + ``_views.xml``
     - includes ``res.config.settings``; the directory is ``wizards/``, not
       ``wizard/`` (§1.1)
   * - Reports
     - ``reports/{model_name}.py`` + ``_views.xml``; QWeb templates
       ``reports/{model_name}_templates.xml``
     - SQL-view report models and ``ir.actions.report`` records; the directory
       is ``reports/``, not ``report/`` (§1.1)

1.4 Machine docs (``machine_doc_v*/``)
--------------------------------------

A module may carry a ``machine_doc_v<N>/`` directory: the machine-readable map of
its routes, models, architecture, conventions and test tags. It is the first thing
read before touching the module, so its figures are adopted as premises. **A wrong
number here is worse than no number.**

**Every figure is gated or frozen. A bare figure is a defect** ``[review]``.

* **Gated** -- derived by the module's ``factcheck.sh`` and asserted with
  ``assert_doc_cites``. A population count is never a literal in the script:
  ``assert_eq "$(measure)" "31"`` makes the script a second copy of the tree.
  Default for anything cheap to re-derive.
* **Frozen** -- pinned to a named base commit, for readings that cannot be
  re-derived (an ad-hoc scanner, a profile, a benchmark). The document states the
  base. **Do not "correct" a frozen figure to a current value**; the surrounding
  argument rests on that base.

Gating governs *measurements*, not *invariants*.
``assert_eq "$(grep -c 'export class Foo' …)" "1"`` is correct -- the literal is
the claim, and it should fail the day the symbol is renamed. Test: would the
number change under ordinary growth? Pin the invariant, not its incidental shape
(``export class Foo extends Bar`` breaks on an inserted intermediate class).

* **Pin every restatement, not just the first.** Prefer not restating it at all.
* **Prefer omitting an incidental figure to gating it.** A number that shapes no
  decision costs context and rots.
* **A harness derives its roots from ``BASH_SOURCE``**, never a literal path.
* **A backticked path asserts that the file exists** -- ``factcheck.sh`` resolves
  every one, including inside a backticked command. Name a deliberately-absent
  file in plain prose.

**A gated figure is measured in the commit that lands it** ``[review]``. The
re-derive is not a fact about the tree, it is a fact about a *commit*, and on a
branch several sessions are landing on those differ within minutes. Worked
example, 2026-08-31: ``bool_return_is_not_a_predicate`` was re-derived in a
detached worktree at ``813b5f68819`` -- correct method, real commit, clean tree
-- and banked at ``7228e38a555``; ``625082c6295`` landed in between and moved the
pair by one, so the figure was **stale on arrival** and needed ``ea62fb88de9`` to
repair. Nothing about the measurement was careless; the window was the review.

* **The window is the gap between measuring and committing, not the measurement**
  -- reading the diff, writing the message and running a suite all widen it.
* **``git log --oneline -1`` immediately before ``git commit`` is the whole
  check.** If HEAD is not what you measured at, re-measure. It is cheaper than
  any of the recoveries.
* **Measure in a detached worktree, never in the checkout**, which is nobody's
  tree while anyone is dirty in it (§12) -- ``--update`` run there banks numbers
  that exist in no branch.

Every discovered ``factcheck.sh`` runs, blocking. Fork-wide assertions SKIP
with a count when this repo is checked out alone.

----

2. Python
=========

2.1 Style and imports
---------------------

* PEP 8, **line length 88** -- what ``ruff format`` produces.
* **Double quotes** everywhere: strings, field attributes, docstrings.
* Import order: stdlib, third-party, ``odoo``, ``odoo.addons``, alphabetical
  within each group ``[ruff I]``.

.. code-block:: python

   import logging

   from odoo import api, fields, models
   from odoo.exceptions import UserError, ValidationError
   from odoo.fields import Domain
   from odoo.tools import LazyTranslate

   from odoo.addons.sale.models.sale_order import SaleOrder

**Reach the ORM through the public façade** ``[test_lint test_orm_import]``.
Addon runtime code imports from ``odoo.api``, ``odoo.fields``, ``odoo.models``,
never from ``odoo.orm``, whose internals the fork restructures freely. Test files
are exempt by location. The boundary is what lets the ORM's internal layout move
without breaking hundreds of addons, and it covers both addon trees: the first
wiring scanned ``odoo/addons`` alone and left seven live bypasses in ``addons/``.

**Format what you write, not the file around it** ``[review]``. Every repo's
``.pre-commit-config.yaml`` runs ``ruff-format`` after ``ruff-check --fix`` and is
the authority on the hook set; there is no gate for formatting, so the hook
reaches only contributors who installed it. Reformatting a file you did not
otherwise change costs twice:

* ``# noqa`` is anchored to a **line**. Reflowing moves the diagnostic off the
  directive: the suppressed finding goes live and the orphaned directive is
  reported as ``RUF100``. Lint, format, then lint again.
* Wrapping spends lines. ``py_function_length.py`` ratcheted excess over the
  limit until it was deleted with ``odoo/tooling/`` in ``7b0f58cb517f``, so a
  pure reformat no longer turns a gate red and **method length is now measured by
  nothing** ``[review]``. The scale, measured 2026-09-15 over the four
  repositories: **6,893** production definitions exceed 40 lines and **952**
  exceed 100, against a median of 11.

Reformatting a whole file is its own commit, justified, with lint re-checked.

2.2 Model class organisation
----------------------------

.. code-block:: python

   class SaleOrder(models.Model):
       _name = "sale.order"
       _description = "Sales Order"
       _inherit = ["mixin.mail.thread", "mixin.mail.activity"]
       _order = "date_order desc, id desc"

Code is grouped under ``# UPPERCASE`` section banners, in this order ``[review]``:

.. list-table::
   :header-rows: 1
   :widths: 6 30 64

   * - #
     - Section
     - Contains
   * - 1
     - ``# FIELDS``
     - field declarations
   * - 2
     - ``# INDEXES``
     - ``models.Index()``
   * - 3
     - ``# CONSTRAINTS``
     - ``models.Constraint()``
   * - 4
     - ``# CONSTRAINT METHODS``
     - ``_check_*`` (and legacy ``_validate_*``, abolished by §2.4)
   * - 5
     - ``# CRUD METHODS``
     - ``create``, ``write``, ``unlink``, ``copy_data``, ``default_get``
   * - 6
     - ``# COMPUTE METHODS``
     - ``_compute_*``
   * - 7
     - ``# SEARCH METHODS``
     - ``_search_*``
   * - 8
     - ``# INVERSE METHODS``
     - ``_inverse_*``
   * - 9
     - ``# ONCHANGE METHODS``
     - ``_onchange_*``
   * - 10
     - ``# ACTION METHODS``
     - ``action_*``
   * - 11
     - ``# MAIL METHODS``
     - ``_message_*``, ``_notify_*``, ``_track_*``
   * - 12
     - ``# <DOMAIN> METHODS``
     - e.g. ``# INVOICING METHODS``
   * - 13
     - ``# HELPER METHODS``
     - ``_prepare_*``, ``_get_*``
   * - 14
     - ``# HOOKS``
     - ``_auto_init``, ``init``, pre/post hooks

Omit sections you do not need. The section *names* are fixed; a surrounding rule
of dashes is cosmetic -- be consistent within a file. Adoption is partial; apply
the layout to files you create or substantially rework. Within
``# COMPUTE METHODS`` and ``# ONCHANGE METHODS``, define a method before the ones
consuming its output. No tool checks ordering.

2.2.1 Mixin naming
~~~~~~~~~~~~~~~~~~

**A mixin's ``_name`` begins with ``mixin.``** ``[review]``, a **prefix**; the
rest of the name keeps the order it had. A mixin is a ``models.AbstractModel``
meant to be inherited *into* other models. Class name and file name follow from
``_name`` by §1.3 and §2.2:

.. code-block:: python

   # models/mixin_mail_activity.py
   class MixinMailActivity(models.AbstractModel):
       _name = "mixin.mail.activity"
       _description = "Activity Mixin"

**What is not a mixin**, and keeps its own name: an abstract model nothing
inherits from. QWeb report models (``report.{module}.{report_name}``) and
abstract service models are ``AbstractModel`` for want of a table.

**Renaming one is a code change, not a data migration.** A mixin has no table;
the stored trace is its ``ir.model`` row (``abstract = True``) and any
``ir.model.data``, both rewritten by the module update. The rename must reach
``_name``, ``_description``, every ``_inherit`` list naming it, the file name, and
every literal model string in XML, CSV or Python -- ``self.env["…"]``,
``<field name="model">``, an ``ir.model.access.csv`` row. The auto-generated
``ir.model`` XML id is ``model_`` plus ``_name`` with dots as underscores, so
every ``ref()`` of it moves with the model. Renaming an inherited *method* to fit
§2.4 remains forbidden (Appendix C); renaming the model is not.

2.2.2 Where a mixin lives
~~~~~~~~~~~~~~~~~~~~~~~~~

**A mixin that depends on ``base`` alone and ships no data lives in ``base``**
``[review]``, beside ``mixin.tag``, ``mixin.tag.nested``, ``mixin.catalog``,
``mixin.image``, ``mixin.band`` and the rest of ``odoo/addons/base/models``. A
module around such a mixin is a directory, a manifest and an
``ir.module.module`` row for one abstract model that every installation loads
anyway: ``base`` is in every closure, so putting the mixin there costs no
dependency and removes a place to look.

**A mixin earns a module of its own on one of two grounds**, and a module that
has neither is a fold waiting to happen:

* **An external dependency.** ``mixin_encryption`` imports ``cryptography``
  at module level; a model in ``base`` may not, because ``base`` must import
  on an interpreter that has only what the framework itself requires.
* **Data, configuration or security of its own.** ``mixin_report_sql`` owns a
  materialized-view lifecycle and its cron; ``mixin_attribute`` carries a
  ``pre_init_hook`` and its own tables. Records need a module to belong to,
  and ``base``'s data is the framework's.

A mixin's ``depends`` beyond ``base`` is a third ground only when the mixin
genuinely reads that module's models; a ``depends`` on ``mail`` for a
``_inherit`` of ``mail.thread`` is real, one copied from a neighbour is not.

**A mixin may instead live with the module that owns its subject matter**, when
one clearly does and every consumer already reaches it. ``base`` is the default
because it is free; a subject-matter home is worth the dependency when it is the
place a reader would look and when it keeps a vocabulary whole rather than
scattering it.

**"Every consumer already reaches it" is a manifest closure, not an
impression** ``[review]``. Compute it before choosing a subject-matter home,
over the consumers the mixin is *for* and not only the ones folding onto it
today:

.. code-block:: python

   # depends closure of each intended consumer; does it contain the home?
   for name in intended_consumers:
       assert home in closure(name), f"{name} cannot reach {home}"

A module that fails this test is not an argument for adding the dependency. It
may be an argument against the home, and if the module is at or below the home
in the graph it is proof against it: the edge would be a cycle and no amount of
subject-matter affinity buys it.

**``mixin_recurrence`` is the worked example, and the test is why it is in
``base``.** It went to ``resource`` first, on the grounds that recurrence is
scheduling vocabulary and ``resource`` is where this fork's scheduling mixins
live. The reasoning was sound about affinity and wrong about reach, because it
was run over the five consumers then folding and not over the question "who
asks how does this repeat".

``ir.cron`` asks it: a count, a unit, ``nextcall`` and a positive-count CHECK
that is the constraint ``mixin.recurrence.interval`` owns -- which is why it now
takes that mixin, as ``repeat_interval`` / ``repeat_unit``, widened with minute
and hour by ``selection_add``. It is the most-read recurrence in the tree
and it lives in ``base``. ``resource`` depends on ``web``, ``web`` depends on
``base``, so a ``base`` -> ``resource`` edge is a cycle: ``ir.cron`` could never
take the mixin, at any price. Six more askers -- ``mail``, and ``event``,
``lunch``, ``gamification``, ``data_recycle`` behind it, plus ``date_range`` --
sit above ``web`` and carry no ``resource``, where the edge is possible and is
not free: ``resource`` ships ``resource.calendar``, ``resource.resource``,
views, menus and demo data, so putting it under ``mail`` installs Resource for
every database that has Discuss.

So the four recurrence mixins -- ``mixin.recurrence.interval``,
``.rule``, ``.rrule``, ``.occurrence`` -- live in ``base``, which is free in
every closure, and ``resource`` keeps the scheduling models that genuinely need
it. ``maintenance`` and ``fleet`` gave back the ``depends`` on ``resource`` the
first fold charged them; ``project``, ``calendar`` and ``planning`` keep theirs
on their own merits. The recurrence-update **dialog** stays in ``resource``:
only ``calendar`` and ``planning`` open it, both carry ``resource``, and
``base`` is no home for a scheduling dialog. A vocabulary and a widget over it
are allowed to live apart.

Nothing stored moved either time -- a mixin has no table (§2.2.1). Both
migrations only re-point ``ir_model_data``, and the second adopts from
``mixin_recurrence`` as well as from ``resource``, because ``base`` upgrades
first and a database that skipped the intermediate release still holds those
rows under the dissolved module's name.

2.3 Field conventions
---------------------

**Group fields semantically, not by type** ``[review]``, each group under a
``# <Noun> block`` comment. Expected on models with roughly ten or more fields.

.. code-block:: python

   class SaleOrder(models.Model):
       # Financial block
       company_id = fields.Many2one(comodel_name="res.company")
       currency_id = fields.Many2one(comodel_name="res.currency")
       payment_term_id = fields.Many2one(comodel_name="account.payment.term")

       # Partner block
       partner_id = fields.Many2one(comodel_name="res.partner")

       # Core identification
       name = fields.Char()
       state = fields.Selection(selection=[...])

       # Order line block
       line_ids = fields.One2many(comodel_name="sale.order.line", inverse_name="order_id")
       amount_total = fields.Monetary(compute="_compute_amounts")

       # UI block
       is_locked = fields.Boolean()

Blocks are per-model -- ``# GPS block`` and ``# Harvest block`` are as legitimate
as ``# Financial block``. Relational fields mix freely inside a block. Line models
open with the ``related=`` fields inherited from their parent, ``order_id`` first.

.. list-table::
   :header-rows: 1

   * - Kind
     - Convention
     - Example
   * - Many2one
     - ``_id`` suffix
     - ``partner_id``
   * - One2many / Many2many
     - ``_ids`` suffix
     - ``line_ids``
   * - Dates
     - ``date_`` prefix
     - ``date_validity``
   * - Amounts
     - ``amount_`` prefix
     - ``amount_total``
   * - Counters
     - ``count_`` prefix
     - ``count_picking``
   * - Quantities
     - ``qty_`` prefix
     - ``qty_transferred`` (core also uses ``product_qty`` / ``qty_done``)
   * - Booleans
     - ``is_`` prefix
     - ``is_sent``
   * - State
     - ``_state`` suffix
     - ``invoice_state``

Defaults that must remain overridable use ``lambda self:``:

.. code-block:: python

   user_id = fields.Many2one(comodel_name="res.users", default=lambda self: self.env.user)

**Every argument is a keyword, in one order, one per line** ``[test_lint E8525,
E8526]``. A positional argument reads as a bare string and only the signature
says whether it is the label, the comodel or the selection; ``comodel_name=``,
``inverse_name=``, ``selection=``, ``string=`` say so. The keywords are read in
the order of ``FIELD_ATTRIBUTE_ORDER`` in
``odoo/addons/test_lint/tests/_checker_field_declaration.py``: what the field
is (``comodel_name``, ``inverse_name``, ``relation``, ``selection``,
``related``), what it says (``string``), its shape (``size``, ``digits``,
``currency_field``, ``translate``, ``sanitize``), how its value is produced
(``compute``, ``inverse``, ``search``, ``depends``, ``precompute``,
``default``), how it is stored and read (``store``, ``index``, ``copy``,
``readonly``, ``required``, ``company_dependent``), what it points at and under
which conditions (``domain``, ``context``, ``ondelete``, ``check_company``),
who tracks it (``tracking``); an attribute the table does not know sorts
alphabetically after those; and last of all who may see it and the help text,
``groups`` second to last and ``help`` last, so the two lines a reader skips
sit together at the bottom. Two or more keywords go one per line, none on the
line of the call -- ruff's magic-trailing-comma layout.
``_sort_field_attributes.py`` in the same directory rewrites a tree to this
form and refuses any rewrite that changes more than argument spelling and
order; a comment inside the parentheses travels with the argument it trails or
precedes.

.. code-block:: python

   partner_id = fields.Many2one(
       comodel_name="res.partner",
       string="Customer",
       compute="_compute_partner_id",
       store=True,
       readonly=False,
       domain="[('is_company', '=', True)]",
       check_company=True,
       tracking=True,
       groups="base.group_user",
       help="The company invoiced for this order.",
   )

**An attribute setup ignores is a dead attribute** ``[test_lint E8527]``:
``index=`` on a One2many, a Many2many or a non-stored compute (no column to
index), ``precompute=`` on a compute without ``store=True`` (dropped with a
warning), and
``compute=`` beside a truthy ``related=`` (replaced by the related path's own
compute). The same holds across ``_inherit``: a ``related=`` that overrides a
field a parent declared with ``compute=`` takes a related field's defaults
(``compute_sudo=True`` unless ``related_sudo=False``, ``readonly=True``), not
the compute's, so it groups and sorts through the join for every user.

**A boolean field attribute takes a Python bool.** ``store``, ``precompute``,
``copy``, ``recursive``, ``compute_sudo``, ``related_sudo``, ``required``,
``readonly`` and ``export_string_translation`` raise ``TypeError`` at
declaration for anything else: ``store="True"`` was truthy, so was
``store="False"``, and no rule that reads ``store=True`` could see either.

**A related field is not stored to make it groupable** ``[test_lint E8529]``. A
``related=`` whose hops are all many2one and whose last field has a column
already filters, groups, sorts and aggregates in SQL through the join, and
``fields_get`` reports it ``groupable``, ``sortable`` and ``searchable``;
``store=True`` adds a copy that every write to the source rewrites on every
child row. Two things need the column and keep it, each with
``# noqa: E8529  <what needs the column>``: a UNIQUE or EXCLUDE constraint over
it (PostgreSQL enforces none across two tables), and a composite index pairing
it with a column of the model's own, where a measured plan says the join
loses. ``Binary`` and ``Image`` are exempt: a stored ``image_128`` is a resize,
not a copy. The existing copies are floored (``lint_stored_related``) and
converted module by module.

**An ``@api.constrains`` naming a related field fires when the source changes,
stored or not** ``[review]``. A stored copy made that happen by accident -- the
recompute is a write on the child, and a write runs its constraints. The ORM now
does it on purpose: ``modified()`` selects a projected field that a constraint of
its model names, finds the records through the trigger tree like any dependent,
and runs those constraints (``recompute._fires_constraints``). So
``@api.constrains("company_id")`` on a line keeps guarding the line when the
*order's* company moves, and keeping ``store=True`` for the sake of a constraint
is not a reason. What still needs the column: a One2many's ``inverse_name``, and
the foreign key behind ``ondelete=``.

2.4 Method naming
-----------------

.. list-table::
   :header-rows: 1

   * - Kind
     - Convention
     - Example
   * - Button actions
     - ``action_`` for **new** methods
     - ``action_confirm``
   * - View openers
     - ``action_view_``
     - ``action_view_invoices`` (``action_open_*`` is valid for wizards)
   * - Compute
     - ``_compute_``
     - ``_compute_amounts``
   * - Prepare values
     - ``_prepare_*_vals``
     - ``_prepare_invoice_vals``
   * - Getters
     - ``_get_``
     - ``_get_candidate``
   * - Onchange
     - ``_onchange_``
     - ``_onchange_partner_id``
   * - Constraints
     - ``_check_``
     - ``_check_date``
   * - Inverse
     - ``_inverse_``
     - ``_inverse_quantity``
   * - Search
     - ``_search_``
     - ``_search_display_name(self, operator, value)``
   * - Mail
     - ``_message_*`` / ``_notify_*`` / ``_track_*``
     - ``_track_subtype``
   * - Default
     - ``_default_``
     - ``_default_warehouse_id``
   * - Domain
     - ``_domain_<field>`` bound; ``_get_domain_<what>`` free-standing
     - ``_domain_child_ids``, ``_get_domain_modules_to_load``
   * - Selection
     - ``_selection_<values>``
     - ``_selection_target_model`` -- named for the values, not the field: one
       method serves fields of several names on unrelated models

**Nothing in this section is mechanically enforced, and its gate markers say
otherwise** ``[review]``. ``odoo/tooling/`` was deleted in ``7b0f58cb517f`` and
took every naming gate with it: ``naming_vocabulary.py``,
``naming_core_vocabulary.py``, ``field_hook_naming.py``,
``collection_head_order``, ``py_function_length.py``, ``ratchet.py`` and
``doc_restated_counts.py``. **Thirty of the thirty-one ``[ratchet …]`` and
``[gate …]`` markers below name one of those**, and the survivor is
``[ruff RUF022]``. ``doc/architecture/gates.md`` is the list of what still runs
and no entry of it reads a method name; ``test_lint``'s ``test_naming.py``
checks one thing, that no public method takes ``ids`` or ``context``. **Read
every naming marker in §2.4 as ``[review]``** until a gate is rebuilt, and read
a sentence that says a gate "now sees" something as history.

**The figures are re-derivable even though the gates are not** ``[review]``, and
the instrument is
agromarin-knowledge/research/2026-09-15-method-naming-census-refresh-evidence --
named in prose because the doc-link gate resolves paths inside this repository
alone. Its ``census.py`` and ``extend.py`` measure a **named commit from a
detached worktree**, which is the condition §2.4.3 already states and which the
shared checkout cannot meet. Re-derive before quoting any number here.

2.4.1 Field hooks
~~~~~~~~~~~~~~~~~

**A field hook is named for the field it serves** ``[ratchet fieldhooks]``. One
field: ``_<attr>_<field>``, spelled in full -- ``_default_category_id``, not
``_default_category``. Several fields: named for what they have in common
(``_compute_amounts``), **never for one of them**. Several *triggers* maintaining
**one** field: named for that field.

**A domain is its own family** ``[ratchet fieldhooks]``. A domain feeds
``search()`` and a field's ``domain=``, never ``create()``/``write()``. Bound:
``_domain_<field>``. Free-standing: ``_get_domain_<what>``. ``_search_*`` is
exempt -- a domain is a search hook's contract. The object leads and the family
marker sits next to the verb; an earlier rule asked only for a ``_domain`` suffix.

**The tail-marked spelling is gated, and the exemption is read off the
annotation, never off the name** ``[gate naming]``. ``base`` was read by hand
and ``_get_eval_domain``, ``_get_action_domain``,
``_get_inheriting_views_domain`` and ``_get_name_search_domain`` all returned a
``Domain`` under the spelling this rule retired -- while ``fieldhooks``'
``unmarked`` kind sees only a body whose every return is a literal, so a domain
assembled in a variable or through ``Domain.AND`` escaped it, and
``naming_vocabulary`` read the addon as clean. ``domain_tail_under_get`` now
reports every ``_get_<what>_domain`` in ``measure()``: the name is the claim,
and a ``_domain`` tail promises a ``Domain``. It is in ``measure()`` and
**not** in ``classify`` on purpose -- ``naming_core_vocabulary`` reads
``classify`` as its ``leading`` kind and pins ``_get_x_domain`` as accepted
there, because its question is whether ``domain`` is a trailing *verb*, which it
is not; widening the shared name test would have moved twenty of ``stock``'s
hard-zero names through a file this rule does not own. *Frozen reading* (§1.4)
at the commit that landed it: **158** in ``addons/``, **78** in ``enterprise``,
**8** in ``agromarin``, **0** in ``design-themes``, and **0** left in ``base``.
Drained by ``42db56e84ac3`` -- 213 names under one substitution and thirteen
read by hand -- so ``addons/`` reads **0** again and the ``naming`` floor is a
contract; the batch also found that ``hr_salary_rule``'s Python columns are
stored code no vocabulary migration had rewritten (§2.4.14).

* **Two honest exceptions share one test.** A hostname (``website``'s
  ``_get_http_domain -> str``) and a record of a model whose own noun is
  *domain* (``mail.alias.domain``'s ``_get_default_domain -> Self``) both wear
  the word for something that is not a search domain. The gate exempts a
  definition whose **return annotation** names a type that is not a domain, and
  holds an unannotated body to its name -- because the name cannot say which
  ``domain`` it means and the annotation can. An unannotated
  ``_get_company_domain`` returning a URL's host is reported, and the repair is
  to say what comes back (``_get_company_host``) or to annotate it; either
  makes the claim checkable.
* **The printed canonical is a hypothesis** (§2.4.8). ``_get_domain_*`` is
  right for the body that returns one; the converse below says what the other
  body is owed.

**And the converse: a ``_get_domain_*`` returns a ``Domain``** ``[review]``. The
free-standing form is a promise about the **return**, not a topic label, so a
method named for what a domain *reads* is named for that instead. ``ir.rule``
carried the pair: ``_get_domain_keys`` returned the **context key names** a
``domain_force`` may consult, and ``_get_domain_context_values`` yielded their
values into an ormcache key -- neither built a domain, and both read at the call
site as though they did. They are ``_get_context_keys_in_domains`` and
``_get_context_values_in_domains``. **The prefix is the family, so it is exempt
from the head-first reordering of §2.4.4**: ``_get_domain_legacy_keys`` and
``_get_domain_accessible_records`` return a ``Domain`` and are already right,
though ``collection_head_order`` scores both ``tail``.

**A hook does one job** ``[ratchet hookpurity]``. Some are not hooks at all: the
declaring model also calls them on ``self`` (calls from tests do not count; the
census table in §2.4.3 counts them). Split it -- the hook keeps the name and
delegates to a helper. The finding survives
any renaming, which is why it is counted apart from the naming rule above.

**A hook's prefix is reserved for hooks** ``[review]``. ``_compute_``,
``_search_``, ``_inverse_``, ``_default_``, ``_onchange_``, ``_domain_`` and
``_selection_`` belong to methods a field declaration points at; a body several
hooks share is named for what it does. Neither field-hook gate sees this, and it
is worst when the field exists: ``ir_cron``'s ``_compute_next_call`` was a
``@staticmethod`` no declaration named, on a model carrying a stored
``nextcall``; it is ``_get_next_call``.

**A ``_selection_*`` method with a parameter is not a hook**: ``selection=`` calls
it with nothing to pass. There are **0** left.

**A field's SQL is declared on the field, never spelled as a model-wide
override** ``[review]``. Three declarations name the model method that composes
a field's SQL, the way ``search=`` names the one that composes its domain:
``value_sql`` (the expression that stands for the field in a query --
``(field, alias, query) -> SQL``), ``group_by_sql`` (its GROUP BY expression --
``(field, alias, query) -> SQL``) and ``order_by_sql`` (its ORDER BY term --
``(field, alias, direction, nulls, query) -> SQL``, returned through
``_order_value_to_sql`` so a term under a grouped query is shaped like a
column's). Where the SQL is another field's, the stand-ins ``group_by_field``
and ``order_by_field`` name it and no method is needed. Setup refuses a hook
that names no method and a hook beside its stand-in. The hook is named for the
declaration and the field, as every field hook is: ``_value_sql_company_currency``,
``_group_by_sql_activity_state``; several fields sharing one body are named
for what they share (``_order_by_sql_activity``).

The reason is what an override hides. ``_field_to_sql``, ``_read_group_groupby``
and ``_order_field_to_sql`` are model-wide: an override that acts on one field
and defers to ``super()`` for the rest is invisible as a per-field fact to
anything that reads the model by its methods -- a reader looking for where
``activity_state`` gets its SQL, a tool keying on method identity, and the Rust
engine's routing gate, which saw thirteen mail-thread models of a plain
database as "read path overridden in python" and served every grouped read on
them from Python for a groupby nobody was asking for. Declared on the field, the
same SQL is a static fact: the engine's export drops a field carrying any of the
three from the kernel's registry, so a query naming it falls back to Python and
every other field on the model routes. **An aggregate of a non-stored compute needs no hook either**: ``_read_group``
selects the group's ids and folds the computed values in Python
(``_aggregates_through_records``), for ``sum``, ``avg``, ``min``, ``max``, the
counts, the arrays, the booleans and ``sum_currency`` -- which is what
``account.analytic.account`` spelled by hand for ``balance``, ``debit`` and
``credit`` in two overrides. The model-method overrides that remain (a custom
granularity, an order term that is not a declared field, an aggregate over a
JSON column) are the ones no field can yet declare.

**What the misused prefix costs is a collision, not a misreading** ``[review]``.
A reserved prefix is a claim that a field declaration somewhere names this
method; while the claim is false the spelling is unowned, and another model is
free to spell a *real* hook the same way. ``hr.employee.public`` carried
``_compute_from_employee``, a shared body eight modules call and no ``compute=``
names, while ``hr.expense.stripe.card`` declares two fields
``compute="_compute_from_employee"`` -- one spelling, two contracts, in two
repositories. ``hr``'s is now ``_update_fields_from_employee``. The same shape
one row down: ``hr``'s ``_get_public_field_names`` read column names for a SQL
view while ``hr_contract_salary``'s method of that name is a ``selection=``
hook. **The rename that repairs the prefix also dissolves the collision**, which
is the argument for doing it before §2.4.4's substitution caution bites: a
workspace-wide ``sed`` cannot tell the two owners apart, and the one that must
run first is whichever is *not* being renamed.

**A protocol namespace may open with a hook prefix, and the prefix does not lose**
``[review]``. **The test is whether the continuation names a field** --
``_search_panel_get_domain_image`` would promise a field
``panel_get_domain_image``, which reads as no field name at all.

**The verb goes after a protocol namespace and in front of a provider one**
``[review]``. A provider prefix (``_gc_``, ``_weasy_``) names *what a value comes
from*: verb first. A protocol namespace is the substring an overrider greps for:
verb behind it -- ``_search_panel_get_*``, ``mail``'s ``_message_post``.

Two readings of the gate itself:

* **Its dedication test is per definition, not per name.** A ``default=`` may
  point at any callable, so the gate reaches one only when the method is
  *dedicated* to the field; counted against raw occurrences, a hook copy-pasted
  into eighteen classes would exempt itself. The census table counts the hooks
  exempt today.
* **The reserved prefixes are worn by more than the hooks**
  ``[gate doc_restated_counts]``. ``field_hook_naming.py --unbound`` counts the
  names, and the definitions under them, that wear one while no field
  declaration and no binding decorator names them (census table). A candidate
  population, not a violation count.

**"Unbound" is a claim about a search, and three things hide a binding from one**
``[review]``. Measured 2026-09-15 by sweeping it: a ``_compute_``/``_default_``
candidate list of **268** came down to **72** renames, and the 196 that fell out
are the interesting part.

#. **The binding is not a string.** A declaration reads
   ``default=_default_company_id`` (a bare name), ``default=lambda self:
   self._default_x()``, or ``default=self._default_x``, and only the *quoted*
   form answers a grep for ``default="_default_x"``. Resolve the keyword's
   **value node** — ``Name``, ``Attribute``, ``Lambda`` — against the AST, not
   its text. In ``addons/project`` and ``addons/project_hr`` the string form is
   the minority of the three, and 68 candidates were bound this way.
#. **The prefix opens a protocol namespace**, which the rule above already
   permits where the continuation names no field.
#. **The tail comes from data.** ``_compute_formula_batch_with_engine_domain``
   is reached through ``f"_compute_formula_batch_with_engine_{engine}"`` where
   the engine is a stored selection value, so no literal caller exists and the
   suffix is not renameable at all (§2.4.14).

**The signature settles it where the body cannot** ``[review]``. A ``compute=``
calls its method with nothing to pass, so **a definition taking arguments is not
the hook it claims to be** — the same reasoning this section already applies to
``_selection_*``, and a fact about the ORM rather than a judgement about the
body. Of the survivors above, the 84 taking arguments were renamed on that
evidence alone.

**A zero-argument survivor is ambiguous, and the two readings have opposite
repairs** ``[review]``. ``_compute_x`` that nothing binds is either a helper
wearing a reserved prefix -- rename it -- or **a field that lost its
``compute=``**, which is a defect the name is the last surviving evidence of.
**Renaming it makes that defect unfindable**: the field stays uncomputed and the
name no longer even claims it should be. So a rename campaign must not answer
this class by construction. Triage it by asking whether a field of that exact
name is declared on the model, then read the body, because the triage is a
filter and not a verdict: of five candidates where the field existed, one
(``document_sign``'s ``_default_folder_id``) was a dead method beside a field
with no ``default=`` at all, while two were live helpers called by the field's
*compute* and named for what they return to it. **When a name and the tree
disagree, the question is which of them is wrong**, and only reading both
answers it.

**A third reading: the field exists nowhere, and the body is dead** ``[review]``.
An ``@api.depends`` body that assigns a field no model declares, and that nothing
binds or calls, serves nothing. Delete it rather than rename it, since a rename
gives dead code a better name. Read in full on 2026-09-16 over the four
repositories, the survivors were **73** definitions under 49 names. Five computed a
field that exists nowhere and were deleted. Two sat beside a real field and were
unbound in upstream 19.0 as well (``account_intrastat``'s
``_compute_intrastat_supplementary_unit_amount``, ``pos_self_order``'s
``_compute_self_order``); binding either changes what a database stores, so both
are left for a decision. Twenty definitions under four names were reached by a
constructed name, three were not on a model, and ``document_sign``'s
``_default_folder_id`` is its owner's question. The other 42, under 34 names, were
helpers and were renamed. **Constructed dispatch counts as a binding**:
``"_default_%s_template_fields" % res_model_name`` binds as surely as ``default=``,
and the whole family renames together or not at all.

2.4.2 Decorator-bound families the gate cannot reach
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``field_hook_naming.py``'s ``ATTRS`` stops at five field-declaration keywords by
construction. A decorator binds the other way round -- the fields are arguments to
the decorator and no field declaration mentions the method -- so four families are
measured by nothing.

**``@api.onchange``** ``[review]``: a hook bound to one field is
``_onchange_<field>``. The census table counts the single-field onchange hooks
and how many are spelled for their field. Four of the rest carry the **pre-9.0
public spelling** (``on_change_login``, ``onchange_parent_id``), reachable over
RPC by accident.

**``@api.depends``'s callable form** ``[review]``. Such a method returns field
names: ``_get_fields_<field>_depends``. A lambda in an attribute the gate *does*
read (``domain=lambda self: …``) is itself the hook, so the method takes the
free-standing form.

**``@api.ondelete``** ``[review]`` binds to no field and its first token is the
*reserved* ``unlink``, so three checkers have no opinion over any of them (census
table).

* ``unlink`` is the right verb: an ``@api.ondelete`` hook deletes nothing, it
  *guards* the ORM operation named ``unlink``. Do not "correct" one to
  ``_remove_``, which names a business method that deletes records.
* **The canonical is ``_unlink_except_<the case that raises>``**, and the census
  table counts how many already carry it. Name the case that raises and take the
  wording from the error:
  ``_unlink_except_master_data`` raises **when** the record is master data, while
  ``_unlink_if_manual`` states the opposite condition.
* ``_unlink_`` is also right for a method that performs the deletion:
  ``_except_`` is a guard and returns, anything else under ``_unlink_`` deletes.
  An ORM-invoked hook is private.

**``@api.constrains``** ``[review]`` is the fourth and largest (census table).
The Validation row governs the spelling and most already carry ``_check_``. The
rest are names the ratchet counts (``_validate_``, ``_ensure_``, ``_verify_``) and
the localisation namespace with the verb behind it
(``_l10n_se_check_payment_reference``). That leaves a residue spelled with a first
token carrying no rule anywhere: ``_constrains_``, ``_constraint_``,
``_limit_available_currency_ids``, and twice the misspelling ``_contrains_``.

**The field-hook rule must not be extended to it** ``[review]``. A hook that binds
exactly one field is not therefore ``_check_<field>``, and the census table shows
how many are not -- that gap is the rule working. A ``compute=`` names a subject;
a ``@api.constrains`` argument names a **trigger**, and a constraint is named for
the **condition it enforces** (``_check_at_least_one_administrator``). The
multi-field constraints named for exactly one of their triggers (census table)
are every one of them right. Ask what **raises**.

**Naming a constraint for its trigger *set* is the same defect as naming it for
one trigger** ``[review]``, and it hides better, because a plural reads like a
condition. ``res.company``'s ``_check_root_delegated_fields`` took its tail from
the ``@api.constrains`` argument -- the callable form, so the trigger list is
literally the method beside it -- while what raises is a subsidiary whose
delegated field differs from its root company's. It is
``_check_delegated_fields_match_root``: state the condition that must hold, on
the model of ``_check_at_least_one_administrator``.

**A hook may hold two bindings, and then one prefix has to lose** ``[review]``.
Do not read a prefix as a claim that no other binding exists.

**``selection=`` is a sixth field-declaration keyword, and ``ATTRS`` stops at
five** ``[ratchet fieldhooks]``. It is not a decorator family -- the declaration
names the method, exactly as ``compute=`` does -- so it belongs to §2.4.1's
mechanism and was missing from it, and the §2.4 table's Selection row was
enforced by nothing. *Frozen reading* (§1.4) at ``45275737cf4``, an ad-hoc
scanner, not re-derivable: **31** field declarations point ``selection=`` at a
method, and **9** of the targets are spelled ``_selection_*``. The other **22**
wear the read verb (``_get_year_selection``, ``_get_check_printing_layouts``) or
no verb at all (``_l10n_bg_document_type_selection_values``). That was the cost
of closing it, and it is nearly all localisation.

**It is closed, and the branch it needed is the whole point**
``[ratchet fieldhooks]``. Adding ``"selection"`` to ``ATTRS`` would have been the
wrong repair, because the Selection row names the hook for its **values** while
every other rule in ``field_hook_naming.py`` asserts the opposite -- that a hook
is named for its field. Run through ``ATTRS`` it would have demanded
``_selection_resource_ref``, ``_selection_parent_ref`` and
``_selection_preview_record_ref`` from three declarations that all point at one
correct ``_selection_target_model``: a rename of exactly the names that are
already right. So ``selection`` is a scope of its own -- ``SELECTION_ATTR``,
reported but deliberately **not** in ``ATTRS`` -- and its whole assertion is the
prefix. **The canonical case is one method serving fields of several names on
unrelated models**, and that is what the branch exists to keep legal.

**And it resolves the forwarding lambda, because that is where the binding stops
being visible** ``[ratchet fieldhooks]``. ``selection="_x"`` and
``selection=lambda self: self._x()`` bind the same method; a branch reading only
the string would have measured the greppable half of the family and called it the
family. The paragraph below argues for writing the name rather than the lambda;
this is the same argument from the gate's side.

**Two of what it found were module-level functions passed by reference, which is
why no earlier count saw them** ``[ratchet fieldhooks]``. Both were in
``odoo/odoo/addons/base`` and are fixed: ``ir.model.fields``'s ``_field_types``
is ``_selection_field_types``, ``res.lang``'s ``_get_date_format_selection`` is
``_selection_date_formats``. A scan that resolves only ``selection="_x"`` reads
neither, and the ad-hoc scanner behind the frozen reading above was such a scan
-- so **the residue is a floor, and the frozen figure is the smaller half of it**.

**A lambda that only forwards hides the binding from whatever reads the
declaration** ``[review]``. ``selection=lambda self: self._x()`` and
``selection="_x"`` bind the same method; the second is a string a grep finds and
a checker can resolve, the first is an AST shape each reader has to know about.
``field_hook_naming.py`` does resolve the forwarding lambda, but only for
``default=`` and ``domain=`` -- its ``_CALLABLE_ATTRS`` -- so for every other
keyword the lambda is where the binding stops being visible. **Where the keyword
accepts a method name, write the name.** The lambda earns its place only when it
computes something the string form cannot express: arguments, a conditional, a
value assembled from the environment.

2.4.3 The verb vocabulary
~~~~~~~~~~~~~~~~~~~~~~~~~

**One verb per operation** ``[review]``. The table in §2.4 governs prefixes
carrying an ORM role; every other method opens with a free verb. The abolished
spellings are wrong, not lesser-preferred. The tree spells single operations many
ways: stems are written with two or more verbs drawn from one semantic family,
and groups of methods share a byte-identical body under different names; the
census table below counts both.

**But the verb is no longer where the duplication is, and that is a measured
result rather than a concession** ``[review]``. Canonical names make redundancy
detectable only while the duplicate pair *differs by a verb*, and the sweeps
have drained that population. Measured 2026-09-15 over ``odoo``, ``enterprise``,
``agromarin`` and ``design-themes`` at ``42ea7357e265`` / ``e793e1375d6`` /
``a8a1a081e`` / ``b284de453``: of **139** groups of definitions sharing an
identical body, **118** already share a name, and applying the
abolished→canonical substitution to the other 21 merges exactly **one**
(``_save_label`` / ``save_label``, and the difference there is the underscore,
not the verb). **The rule's own mechanism now reports one candidate.** Where the
residual duplication actually lives is two shapes this section does not name:

* **A namespace-prefixed sibling.** ``_l10n_ae_get_company_wps`` /
  ``_l10n_sa_get_company_wps``, ``_dk_build_zip_response`` /
  ``_ee_build_zip_response``, ``_envia_convert_weight`` /
  ``_shiprocket_convert_weight``, ``_add_invoice_line_price_nodes`` /
  ``_add_purchase_order_line_price_nodes`` / ``_add_sale_order_line_price_nodes``.
  The verbs already agree; the discriminating token is the country, carrier or
  document the body is identical across, which is the tell that the body belongs
  one layer down.
* **The same name copied into sibling modules.** ``debug_log.py`` is duplicated
  verbatim into six addons, ``l10n_be_hr_payroll`` carries nine identical
  ``default_get``, ``l10n_ch_hr_payroll`` four identical ``_get_declaration``.
  No naming rule can see these, because nothing is misnamed.

So **run the body comparison, not only the name search**: `clones.json` and
`repeated-blocks.csv` in the evidence directory above are that report, and the
block view is the sharper of the two -- **1,128** repeated three-statement
windows across **2,527** sites, **1,375** of them inside a method longer than 40
lines, which is the extraction backlog stated as a number. §2.4's order stands
(naming → redundancy detection → logic improvement); what has changed is that
step one is finished for verbs and step two now needs a different instrument.

**Every figure in this section was measured, not stated** ``[review]``. The
population is the non-test methods declared on a model class **in this
repository** -- the population ``naming_vocabulary.py`` ratcheted, and the first
§2.4.3 row of the census table. The census stops here, so every figure is a
floor.

**The census table is a FROZEN reading now, not a current one** ``[review]``.
``doc_restated_counts.py`` was deleted with ``odoo/tooling/``, so no ``--update``
and no ``--check`` exists: the block states the tree as it stood when the tool
last ran and **nothing has refreshed it since**. Re-derived 2026-09-15 at
``42ea7357e265`` with the instrument named at the head of §2.4, **10 of its 59
rows are still true**, and the three ways a row fails are different problems:

* **33 rows are reproducible** from the prose alone -- a prefix count, a
  decorator count -- and 23 of those have moved. The loudest are the campaign's
  own signal: ``_prepare_*`` 911 → **1,598** and ``_set_*`` 126 → **83**, which
  is the payload sweep of §2.4.7 landing. ``_get_*`` 6,553 → 6,518,
  ``_check_*`` 1,281 → 1,389, ``inverse=`` targets 269 → 374.
* **19 rows are approximable but not exact**, because the prose fixes the
  family and not the population: "field hooks the declaring model also calls on
  ``self``" does not say whether a call from a sibling file counts.
* **7 rows cannot be re-derived by anybody.** Their population lived in
  ``naming_vocabulary.py``'s ``_COLLECTION_HEADS`` tuple and its
  ``_HEADS_HEAD_FIRST`` regex -- which heads were searched, and the requirement
  of a token after the head. Those are the five §2.4.4 head/tail rows and the two
  §2.4.5 converter rows. A re-measurement answers a **different question** and
  is not comparable; the cautions four paragraphs down in §2.4.4 describe a
  measurement nobody can now run.

**That is the durable lesson, and it is about where a definition lives rather
than about a number** ``[review]``. A figure whose population is defined only
inside a tool dies with the tool, while a figure whose population is defined in
the sentence beside it survives. **State the population in the prose, in enough
detail to re-derive it**, and treat a count that needs a deleted classifier to
mean anything as prose that was never finished. A count whose only job is to be
current still belongs in this block and nowhere else, and re-deriving the block
is now a scripted measurement recorded in the vault rather than a ``--update``
flag.

**Who re-derives it, and when** ``[review]``. The block goes stale on every
rename that touches ``odoo/`` or ``addons/``, which in a workspace where several
people are sweeping at once is most of them, and it once stood **thirteen rows**
stale because each of four sessions correctly established the rows were not
theirs alone to bank. The rule that failed was *whoever lands last re-derives it*.
**"Last" is not a state a session can observe** -- it is a claim about a boundary
that moves the next time anybody commits, so it resolves to nobody and the block
rots. The rule that works is checkable by the person it binds:

  **Whoever moves a row after the last bank owns the next one.** Run
  ``--check`` after committing a rename; if a row moved, re-derive it or hand it
  to someone who will.

* **Bank from a detached worktree at your own commit, never from the checkout.**
  The tool measures whatever tree you point it at, and a shared checkout holds
  everyone's uncommitted work, so an ``--update`` there banks other people's
  unlanded renames as the branch's figures. §2.4.14's shelf-life rule, applied to
  a number: the reading is true of a tree, and only a commit names one.
* **Two correct measurements can contradict each other, which is the whole
  argument.** Two sessions read ``heads_tail_first`` as **162** and **161** on the
  same row, from the same gate, with no rename of that shape between them; the
  only variable was the minute each ran it. Neither was wrong and neither was
  about the branch.
* **The question before banking is not "is the tree dirty" but "is anyone else
  renaming inside this row's population".** A clean tree does not make a contested
  row yours and a dirty one does not make an uncontested row somebody else's. A
  figure whose population nobody else is touching is safe to bank from a dirty
  checkout -- ``migration_scripts`` was, correctly, after one ``git status``
  confirming no uncommitted file contributed to it.
* **``--update`` takes row names and writes every unselected row back
  as-stated**, so a partial bank is safe and is the right tool for one row you
  distrust with no contest over it. Prefer the whole block when the whole block is
  contested, which is the ordinary case here.
* **A figure a sentence reasons from takes the sentence with it.** Draining
  §2.4.13's nested backlog to **0** left a bullet whose grammar still called it a
  backlog -- a stale figure one level up, and one no gate can see. Reword in the
  same commit.
* **Transfer the rows as anchored hunks; do NOT copy the file back.** The
  worktree is where you MEASURE. Writing its whole ``coding_guidelines.rst`` over
  the checkout's is a whole-file write into a file several sessions hold hunks in,
  which is §2.4.20's own destruction wearing the look of housekeeping -- ``cp``
  out of a worktree is the same shape as ``git checkout --``. Apply each changed
  row to the live file and re-read its anchor immediately before writing.
* **A worktree carrying your edit will tell you the tree is already fresh.**
  ``git checkout --detach`` moves an uncommitted file forward with you, so a
  ``--check`` run after re-pointing the worktree reads the answer you brought
  rather than the tree: it reported *fresh* against a tip whose fifteen rows were
  stale, and discarding the edit showed them all. Verifying that YOUR figures are
  true of a commit and asking whether THAT COMMIT's doc is fresh are the same
  command and different questions -- the second one is only answered by a tree
  you have not written to.
* **Re-read the tip after measuring and refuse to transfer if it moved.** One
  ``git rev-parse`` before and after. On an evening with five sessions landing,
  the tip moved four times in a few minutes and the guard refused twice before
  letting a bank through; the figures happened to be identical at all four tips,
  which is exactly why the check has to be mechanical rather than a judgement
  about whether the move "could have mattered". It is the difference between a
  figure that describes a commit and one that describes a moment.

.. census-table-start

=======  =========================================================  ======
Section  Population                                                  Count
=======  =========================================================  ======
§2.4.1   Field hooks the declaring model also calls on ``self``         13
§2.4.1   Field hooks exempt from the dedication test                     0
§2.4.1   Names wearing a hook prefix with no binding                   166
§2.4.1   … definitions under those names                               234
§2.4.2   Single-field ``@api.onchange`` hooks                          393
§2.4.2   … spelled ``_onchange_<field>``                               287
§2.4.2   ``@api.ondelete`` hooks                                       173
§2.4.2   … spelled ``_unlink_except_*``                                114
§2.4.2   ``@api.constrains`` hooks                                     728
§2.4.2   … spelled ``_check_*``                                        673
§2.4.2   … with a first token carrying no rule                          50
§2.4.2   … binding exactly one field                                   329
§2.4.2   … of those, spelled ``_check_<field>``                        145
§2.4.2   Multi-field constraints named for one trigger                  62
§2.4.3   Non-test methods declared on a model class                 27,490
§2.4.3   Stems spelled with two or more verbs of one family              1
§2.4.3   Groups of methods sharing a byte-identical body               106
§2.4.4   Model methods with an abolished verb behind a noun            171
§2.4.4   Canonical verb behind a first token carrying no rule          681
§2.4.4   Model methods opening with ``auto`` fused to a verb            13
§2.4.4   ``fields`` family: definitions spelled head-first             224
§2.4.4   ``fields`` family: distinct names spelled head-first           99
§2.4.4   ``fields`` family: definitions spelled tail-first              32
§2.4.4   Other collection heads the census searches                     19
§2.4.4   Other heads: definitions spelled head-first                   150
§2.4.4   Other heads: definitions spelled tail-first                   197
§2.4.5   ``X_to_Y`` converter definitions                              103
§2.4.5   … distinct names                                               56
§2.4.7   ``_get_*`` definitions                                      6,553
§2.4.7   Abolished payload verbs, the four between them                  0
§2.4.7   ``_generate_*`` definitions                                   122
§2.4.7   ``_calculate_*`` model methods                                  0
§2.4.7   ``_prepare_*`` definitions                                    911
§2.4.7   … calling ``create()``, ``write()`` or ``unlink()``            37
§2.4.8   ``_check_*`` definitions                                    1,281
§2.4.8   ``_validate_*`` definitions                                     0
§2.4.8   ``_verify_``, ``_ensure_`` and ``_control_`` together           0
§2.4.9   Execution-verb definitions, ``_do_`` through ``_handle_``     184
§2.4.10  ``_raise_*`` model methods                                     21
§2.4.10  … raising unconditionally                                      12
§2.4.11  ``_find_*`` methods                                            17
§2.4.11  … performing an ORM read                                        1
§2.4.11  … doing something else entirely                                15
§2.4.11  ``_find_or_create_*`` methods                                   1
§2.4.11  ``_get_or_create_*`` methods                                   34
§2.4.11  ``_resolve_*`` definitions                                     29
§2.4.12  ``_set_*`` definitions                                        126
§2.4.12  ``_update_*`` definitions                                     425
§2.4.12  ``inverse=`` targets spelled ``_inverse_<field>``             269
§2.4.12  ``inverse=`` targets spelled ``_set_*``                         1
§2.4.12  ``_sync_*`` definitions                                        93
§2.4.12  ``_synchronize_*`` definitions                                  0
§2.4.12  ``_post_*`` definitions                                       144
§2.4.13  Module-level functions under ``models/`` and ``wizard/``      365
§2.4.13  Methods on plain classes in model files                       421
§2.4.13  … such classes                                                169
§2.4.13  Functions nested inside model methods                         659
§2.4.14  Private method names reached from stored Python               118
§2.4.14  … code blocks reaching them                                   128
§2.4.14  … shipped data files holding those blocks                      76
§2.4.14  Classes implementing ``_get_report_values``                    19
§2.4.14  … ``get_values``                                               12
§2.4.14  … ``set_values``                                               21
=======  =========================================================  ======

.. census-table-end

.. list-table::
   :header-rows: 1
   :widths: 12 16 34 38

   * - Family
     - Canonical
     - Abolished
     - Discriminator
   * - Payload
     - ``_prepare_*``
     - ``_build_`` ``_make_`` ``_compose_`` ``_construct_``
     - the return value feeds ``create()`` / ``write()`` / ``Command``
   * - Read
     - ``_get_*``
     - ``_fetch_`` ``_retrieve_`` ``_obtain_`` ``_lookup_``
     - the return value feeds anything else -- see §2.4.7 before reading this as
       "does not build it"
   * - Predicate
     - ``_is_`` ``_has_`` ``_can_``
     - --
     - **the returned ``bool`` is the answer to a question about the subject**;
       never raises, no side effect. The return *type* is not the test
   * - Validation
     - ``_check_*``
     - ``_validate_`` ``_verify_`` ``_ensure_`` ``_control_``
     - **raises** on failure; a boolean answer is a predicate
   * - Mutation
     - ``_update_*``
     - ``_assign_`` ``_fill_`` ``_inject_``
     - writes to records; an ``inverse=`` target is ``_inverse_<field>``
   * - Addition
     - ``_add_*``
     - ``_append_`` ``_fill_`` (of a caller's container)
     - adds entries to a container — records' x2many, or a dict or list **the caller
       passes in** and reads back; ``_insert_`` / ``_push_`` are reserved, not abolished
   * - Removal
     - ``_remove_*``
     - ``_delete_`` ``_purge_``
     - ``unlink`` stays reserved for the ORM operation; so do ``_drop_`` /
       ``_discard_``

**An accumulator is Addition, not Payload and not Mutation** ``[review]``. A body that
writes into a dict or list its caller hands it, and returns nothing, fits neither of
the rows it resembles: ``_prepare_`` *returns* the payload, and ``_update_`` writes
*records*. The shape is common where one report or document is assembled in passes —
``account_saft``'s ``_saft_fill_report_*`` family filling one ``values`` dict, one
section at a time — and it was spelled ``_fill_`` because no row claimed it. It is
``_add_``: the method adds its section to a container the caller owns and will read
back. **The discriminator is who holds the container**; a body that builds a dict and
returns it is still ``_prepare_``, and one that writes onto records is still
``_update_``.

**Reserved, not abolished** ``[review]``. Each is a term of art from a layer
below the ORM; collapsing it destroys information. Use them **only** with these
meanings -- a business method that deletes records is ``_remove_*``, never
``_drop_*``, and a predicate is never spelled with ``exists``.

.. list-table::
   :header-rows: 1
   :widths: 16 84

   * - Verb
     - Reserved for
   * - ``_drop_``
     - SQL DDL -- ``_drop_table``, ``_drop_column``
   * - ``_insert_``
     - SQL DML and ordered insertion -- ``_insert_cache``, ``insert_rows``
   * - ``_push_``
     - stack or queue semantics -- ``push_protection``
   * - ``_discard_``
     - the ``set.discard`` contract: remove if present, never raise
   * - ``_append_``
     - an ordered sequence whose **position is part of its contract**; abolished
       everywhere else, which is the common case
   * - ``read`` / ``write``
     - a method whose object is a **file** -- the pair names one contract and
       must not split across ``_get_`` and ``_write_``
   * - ``_resolve_``
     - a **partial** producer: returns the object, or ``None`` meaning *not
       applicable* (§2.4.11)
   * - ``_sync_``
     - convergence on a source of truth elsewhere (§2.4.12)
   * - ``fetch``
     - the ORM read operation that loads stored values into the cache. The
       public ``fetch()``, its internals ``_fetch_field`` / ``_fetch_query``
       and the port's ``backend.fetch`` are **one** contract, so they are
       renamed together or not at all (§2.4.11); ``_get_query`` would promise
       a ``Query`` return
   * - ``flush_``
     - the ORM operation -- ``flush_model``, ``flush_recordset``
   * - ``_evict_``
     - **capacity** eviction: which entries go, not whether what stays is valid
   * - ``exists`` / ``_*_exists``
     - the ORM operation ``recordset.exists()``, and schema introspection --
       ``_table_exists``, ``_column_exists``

**Every row is a claim about a *layer*, not about a word** ``[review]``, and a
reader who greps the table for the verb gets the answer wrong in both directions.
``_drop_`` is reserved for SQL **DDL**, so ``service/db/lifecycle.py``'s
``_drop_conn`` -- which issues ``pg_terminate_backend`` -- was never in the row
and is ``_terminate_backends``. The other direction cost more, because it looks
like obedience: ``assetsbundle``'s ``_addon_relative_path_exists`` asks the
**filesystem** whether an addon-relative path resolves, and the ``exists`` row
covers ``recordset.exists()`` and schema introspection, neither of which is a
file. It is ``_is_addon_path_present``, an ordinary predicate. **Where an
operation belongs to a layer the row does not name, the reservation has no
opinion and the ordinary vocabulary applies** -- and a reservation the ordinary
vocabulary was not allowed to reach is how one question ends up asked twice:
``_addon_is_present`` sat four lines above it, spelling the identical question in
the other grammar.

**And the same rule in the other direction: a reserved row can outrank the
abolished row's printed canonical** ``[review]``. Above, a reserved row failed to
claim a name that looked like its own; here one wins a name the abolished table
had already assigned. The Mutation row abolishes ``_inject_`` and prints
``_update_*``, but ``orm/model_test_env.py``'s ``_inject(table, record_id, data)``
calls ``storage.put_rows`` -- it is **DML**, the layer ``_insert_`` is reserved
for. It is ``_insert_row``, and ``_update_*`` would have been wrong. §2.4.8 says
the ratchet's suggested target is a hypothesis rather than a verdict; this is
that rule one table up. **Read the row's scope against the body: where an
abolished row and a reserved row both reach a name, the reserved one can win.**

**Before claiming ``_append_``, check both halves**: a receiver that is a
sequence, and an addition that lands at its end. ``naming_vocabulary.py`` keeps
``append`` in ``ABOLISHED`` unconditionally -- it reads a name, not a receiver --
so the reservation is ``[review]`` and widens no gate.

**Two of these rows are gated; the other five are not, and the split is about
what an AST can settle** ``[gate naming]``. ``RESERVED`` was declared in
``naming_vocabulary.py`` from the start and ``measure()`` consulted none of it --
it fed the census and nothing that could fail -- so *a reserved verb worn by a
method that does not do the reserved thing* was the one shape this section
defined and no gate enforced. ``_drop_`` and ``_insert_`` now are, because their
rows are claims about the **body**: SQL DDL, and SQL DML or ordered insertion. A
definition earns the verb by running the statement (``cr.execute``, an ``SQL()``
call, a DDL/DML literal) or by assembling a fragment of one for a caller that
runs it -- ``ir.model.data._insert_xmlids_extra_columns`` returns
``dict[str, SQL]`` for an ``INSERT`` it never issues, and is named for that
statement correctly, so a return annotation naming ``SQL`` earns it too.
``_insert_`` additionally earns it from a **caller-given position**, which is the
ordered-insertion half: ``ir.asset.paths.insert_paths(paths, bundle, index)``
places a member where its caller says, while ``project``'s ``_add_view_mode(
xmlids, view_type, before=None)`` computed its own index and was being asked to
*add* one.

The other five rows stay ``[review]`` because no reading of a function body
separates them from their ordinary counterpart: *one string in, one typed value
out* from a ``_read_`` of a file, a keyed encoding from a format, a key-to-member
mapping from a search index, a stack from any other addition, or
``set.discard``'s contract from a raise. **Enforcing two is not a finding that
five are clean** -- it is the whole checkable half of *this* dict, and a gate
that guessed at the rest would report ``_parse_date`` wrong for doing exactly
what its verb reserves.

**Nor is it a claim that the gate is now complete**, and the nearest
counter-example is one section down: until 2026-09-09 §2.4.13 recorded that
``ADDON_HELPER_DIRS`` was ``{models, wizard, wizards}``, so an addon's
``controllers/`` was in **this** gate's population at no scope. That was a hole
in the **population**; this was a hole in the **rule**, and they composed -- a
reserved verb misused in a controller was reached by neither. The population
hole is closed (§2.4.13); read the rule half as no completeness claim either.

**Say which gate, though.** ``naming_core_vocabulary.py``'s ``scan_files`` is
``rglob("*.py")`` minus ``SKIP_DIRS`` and the test suites, with no helper-dirs
filter at all, so a tree in its ``GOVERNED_ADDONS`` has its ``controllers/``
read for free -- which is how ``sale``'s ``_determine_is_down_payment``, in
``sale/controllers/portal.py``, was reported. Written as *no gate reaches
controllers*, the sentence would take the repair with it: §2.4.13's fix for an
absent scope is to onboard the tree to the gate whose population is already
right, one element of a tuple and a hard zero from that moment, rather than to
widen the gate whose population is wrong and pay for it in every repository.

What the enforcement cost, measured on landing: **17** definitions across the
four repositories, all but one of them private, and every one contained in its
own file except two: ``agromarin``'s ``_remove_already_stored``, declared once
per model in ``remote_mobile``, and the ``view_mode`` family, which is three
methods in ``project`` reached from two ``<function>`` records in ``enterprise``
(§2.4.14) and mirrored by one more in each of ``project_gantt`` and
``project_map``. All four scopes returned to the floors they already
held -- ``naming`` 0, ``naming_enterprise`` 213, ``naming_agromarin`` 0,
``naming_design-themes`` 0 -- which is the re-derivable half of this paragraph
and the reason the tightening banks no increase. **Not all in one commit,
though**: one of the seventeen,
``stock_move_done._remove_unpicked_lines_and_cancel_empty``, was carried into
another session's sweep of the same file, because a pathspec commit takes the
WORKING-TREE content of the paths it names and §12's index discipline does
nothing about a peer's dirty tree inside your own paths. Nothing was lost and
the branch holds the rename; the lesson is that *the rule and the renames it
forced need not end up in one commit even when one session made all of them*,
so the count above is a property of the tree and not of any commit -- read it
that way, and check the floors rather than the log. The **17** is
a *frozen* reading (§1.4): it is what the rule cost at landing, and the tree no
longer holds it. It was taken in a shared checkout several sessions were
renaming in, which §2.4.3 says is the wrong place to take a figure -- so it was
checked the one way that works for a set this small rather than re-taken in a
worktree: every one of the 17 names was confirmed present at ``HEAD``, at the
same occurrence count, with ``git show HEAD:<path>``. The figure describes the
branch and not anybody's uncommitted work. **Choose the instrument by the size
of the set**: a per-name ``git show HEAD:`` needs no worktree and settles 17
enumerated names in one command, while §2.4.13's 61 -- a population nobody can
list -- needs the detached worktree, and got one, because the shared checkout
read 63 for the same scope the same afternoon. Do that, or measure at a commit;
a count of this shape read off a dirty checkout and left unchecked is the
failure §2.4.3 opens with. The family is the argument for the rule: ``project`` had
``_insert_view_mode`` beside ``_remove_view_mode`` and ``project_gantt`` and
``project_map`` each had their own ``_insert_*_view_mode``, so one operation was
spelled with the removal's non-pair in four modules at once, and §2.4.3's own
Addition row had said ``_add_*`` the whole time.

**The reservation binds public names too**, and three are left as found because
renaming them is owed a public-surface weighing and one change across every
repository:
``ir.actions.server``'s ``create_action`` and ``unlink_action``, which perform
neither operation they name, and ``ir.cron``'s ``method_direct_trigger``.

**``_apply_`` is the Mutation row's largest unlisted spelling** ``[review]``.
The three verbs that row abolishes are rare; ``_apply_`` is **126** definitions
under **84** names, and most of them write to records and are wired to nothing,
which is the row's own description of ``_update_``. It survives because it reads
as a verb and because a minority of its uses are honest -- applying a *named
policy* to something (``_apply_putaway_strategy``, ``_apply_cash_rounding``),
where the object is the policy and not the record. **The test is the object**:
apply a strategy, a rule, a rounding, a discount -- update a record, a field, a
quantity. ``_apply_qty_available`` failed it and is ``_update_qty_available``. It
is not in ``ABOLISHED`` because that split needs the body, and a stem test would
take the honest half with the rest.

**Look for the same operation on the other half of a paired model** ``[review]``,
and only then is the verb question decidable. §2.4.12 says a ``_set_x`` beside an
``_update_x`` is the duplicate report this section exists to produce; the shape
that hides from that search is one operation split across two **models** that
mirror each other -- template and variant, order and line, move and move line,
picking and move. ``product.template._set_qty_available`` and
``product.product._apply_qty_available`` were one operation under two verbs, each
reached from a method the two models spell **identically** (``_inverse_qty_available``),
so the pair was invisible to a search on either name and visible immediately from
the caller they share. **Where two paired models implement the same operation,
read both spellings before choosing either**; the shared caller is where to look.

**Two verbs for one operation is a duplicate report only when neither verb is a
noun the file already owns** ``[review]``. This is the guard on the rule above,
and a sweep run mechanically will trip it. ``ReachabilityProbe`` declares
``check_connectable``, which consults the proven set and the in-flight table,
and ``probe_connectable``, which opens the connection -- two verbs, one
operation, adjacent, exactly §2.4.3's shape. They are **not** a duplicate:
*probe* is a **noun this file declares**, in ``_InFlightProbe``,
``PROBE_CONNECT_TIMEOUT``, ``record_probe_started`` and
``record_probe_outcome``, so the second verb is carrying the module's own
concept rather than a second spelling of the first. **Ask whether the verb
appears as a noun in the same scope before collapsing a pair** -- where it does,
the pair is a decision and an act, and both names are load-bearing.

**A reserved verb frozen into a wire name is a reason to look, not a reason to
keep** ``[review]``. ``odoo/db``'s ``PoolStats`` counts pools dropped because
their credentials changed, under ``pools_evicted_stale``, which
``service/metrics.py`` exports as ``odoo_pool_evicted_stale_total``. The
reserved row above gives ``_evict_`` to **capacity** eviction -- which entries
go, not whether what stays is valid -- and a credential change is the other
question entirely, so the Python half is misnamed and the Prometheus half is a
§2.4.14 binding that cannot move without a scrape-config change in every
deployment. **The wire name does not license the verb in Python**, and the two
halves parting company is the ordinary outcome, not a failure: rename inside
the workspace, leave the exported key, and say in the commit which half you
left. This one is left whole, and is named here so the next sweep does not
rediscover it as new.

2.4.4 Ordering
~~~~~~~~~~~~~~

**The verb leads** ``[review]``. ``naming_vocabulary.classify`` partitions on the
first token and stops, so a noun in front of the verb hides the verb from the rule
*and* from its enforcement: ``_import_retrieve_partner_vals`` scores as the verb
``import``, which carries no rule. Backlog (census table): the model methods that
put an abolished verb somewhere the ratchet cannot read it are a candidate
population, since some of those tokens belong to a noun or a field name.

**The hidden verb is as often the canonical one** ``[review]``, and that shape
is the second candidate row. ``_push_prepare_move_copy_values``,
``_log_activity_get_documents``, ``_delay_alert_get_documents`` and
``_stock_picking_check_access`` all carried the row's own verb one token behind a
first token carrying no rule, and read to the gate as correctly named -- there
was no abolished word to see. The census counts the model methods whose first
token is governed by nothing (no verb from any table, no hook or predicate
prefix, no ORM operation, none of the protocol namespaces below) and that carry
``prepare`` / ``get`` / ``check`` / ``update`` / ``add`` / ``remove`` somewhere
after it. It is a candidate list for the same reason the abolished one is:
``_ubl_add_*`` and ``_stripe_get_*`` sit in it and are namespaces this section
admits, and nothing mechanical separates a protocol prefix from a noun parked in
front of the verb. Read it grouped by first token.

**Grouping by first token sorts the list; the size of a group does not sort it**
``[review]``. An earlier form of this rule said a token with one member is almost
always a noun and one with sixty is almost always a namespace. The first half
holds and **the second is false**, which matters because it was the half that
licensed skipping the big groups. Measured 2026-09-15 over the four repositories:
**18,148** production definitions open with a token carrying no rule from any
table in §2.4, under **2,333** distinct tokens, of which **988** have exactly one
member and **39** have sixty or more. Read those 39, and the majority are not
namespaces but **verbs the table does not print** -- ``generate`` 400,
``parse`` 279, ``format`` 273, ``convert`` 222, ``extract`` 177, ``merge`` 122,
``filter`` 109, ``find`` 89, ``split`` 85, ``normalize`` 75, ``save`` 70,
``sanitize`` 56 -- beside the genuine namespaces ``l10n`` 1,778, ``cron`` 208,
``message`` 196, ``mail`` 121, ``web`` 108, ``ubl`` 91, ``portal`` 83. **A big
group is the most likely place for an unlisted verb, not the safest place to
stop**, and §2.4.20 is where an unlisted verb is resolved.

**The discriminator is the token's grammar, not its frequency** ``[review]``.
Ask the two questions that already appear in this section: could the token follow
*which* or *whose* (then it is a qualifier or a namespace), and would the prefix
survive being moved to another model (then it is a protocol). A token that
answers *what does this do* is a verb wherever it sits, and ``l10n`` is the
proof that size decides nothing: it is the largest ungoverned token in the tree,
it is a namespace, and its 1,778 definitions average 33.4 lines against the
tree's median of 11 -- the longest family in the census after the getters,
which makes it the first place §2.4.9's splitting work should look rather than
the last.

* A noun-first prefix is legitimate only where it names a **protocol several
  models implement** (``_message_*``, ``_notify_*``, ``_track_*``,
  ``_portal_*``), never as a per-model tidy-up. **The test is not size: ask
  whether the prefix would survive being moved to another model.**
* **A name with no verb at all is the same blind spot with nothing behind it.**
  Repair is mechanical -- verb, object, qualifier: ``_root_model_names`` is
  ``_get_model_names_in_root_table``.
* **A namespace has to be a namespace in every name that wears it.**
  ``_gc_file_store`` reads *gc the file store* while ``_gc_checklist`` reads *the
  gc checklist*, and is ``_get_gc_checklist``. Look for the member that already
  has a spelling before choosing one.
* **Layer the namespaces in the order the calls nest.** ``_esm_run_esbuild``
  wrapping ``_esbuild_invoke`` put each prefix on the other's operation; the pair
  is ``_compile_with_esbuild`` and ``_compile_with_esbuild_locked``.

**A public method drops the underscore, not the verb** ``[review]``. The public
form of a getter is ``get_*``, of a payload builder ``prepare_*``, down the table.
**A public rename is weighed differently**: an RPC caller leaves no
trace in any tree a gate can scan, so weigh it as a public-surface change, give it
and rewrite every repository in one
change or none. **A rename that cannot be completed inside the workspace is not
begun.**

* **A word in front of the verb that is not a namespace is a modality, and it
  belongs in the tail as a condition** ``[review]``. §2.4.6 sends a trailing
  adverb to the tail; the harder case is the one in front, because it passes the
  namespace test by looking like a prefix. ``_safe_close`` and ``_safe_drain``
  swallow the pool's exceptions during teardown, and *safe* answers neither
  *whose* nor *which* -- it says **how**, which is the tail's job:
  ``_close_pool_safely`` and ``_drain_pool_safely``, which also recover the
  object both names had dropped. ``_maybe_`` is the same word wearing a
  condition: ``_maybe_reap_idle_pools`` reaps only when the reaper's interval
  has elapsed, and is ``_reap_idle_pools_if_due`` -- **write the condition, not
  the hedge**, because *maybe* is true of any method with an early return.
  **``auto`` is the same word fused to the verb**, and the fusion is what hides
  it: ``classify`` reads ``autoprint`` as a verb carrying no rule, where a
  ``_safe_`` at least stands alone for a reader to see. ``mrp``'s
  ``_autoprint_generated_lot`` returned a report action, so it takes the row its
  return earns -- ``_prepare_action_autoprint_generated_lot``, on the spelling
  ``stock``'s ``_prepare_actions_autoprint`` had already chosen -- and
  ``_autoconfirm_production`` confirmed the draft moves and workorders of an
  order, which is what its name now says. The census counts the population
  ``[gate doc_restated_counts]``; it is a candidate list rather than a rule,
  because ``autovacuum`` and ``autocomplete`` are terms of art that fuse the
  same way.

**The signature can prove the public spelling was an accident** ``[review]``. A
return of recordsets, callables or exceptions -- anything that does not survive
serialisation -- is evidence the missing underscore was an oversight, since the
one call that would make it a public contract raises rather than returns. So is a
**required** parameter no JSON-RPC request can carry: a recordset, a
``fields.Field``, a ``Callable``, an ``Environment``, a cursor. Making such a
method private *removes* a surface, so the public-rename weighing does not apply.
Where
``model_member_surface_check.py`` pins the name, the pin moves in the same change
or the gate fails both ways.

**The object leads its qualifier** ``[review]``. A name returning a qualified
thing puts the **thing** first: ``_get_fields_readable``, not
``_get_readable_fields``; ``_get_port_effective``, not ``_effective_port``. Not a
rule about collections -- a scalar with an adjective reads the same way.

**Head-first is a test as well as an ordering** ``[review]``. Apply the reordering
and **read the result**:

**A ``@property`` is named for the value, not the operation** ``[review]`` -- the
one exception to *the verb leads*. An attribute access is not a call, so nothing
at the call site is looking for a verb, and applying the rule literally wrecks
names that are already right: ``best_lang``, ``nodb_routing_map``,
``session_store``, ``geoip_city_db``, ``country_code``. The rest of this section
still governs the noun -- ``_city_record`` and ``_country_record`` are head-first
and distinguish each other -- and a ``@property`` returning ``bool`` may be an
adjective (``closed``, ``enabled``, ``is_qweb``), because §2.4.8's three prefixes
are for methods, which are asked rather than read.

**And no tool can tell a property from a method**, because both are a ``def``.
That is the expensive half: every no-verb scan in this section sweeps the
property population in unless it filters the decorator first, and the filter is
what makes the result readable rather than the scan. *Frozen reading* (§1.4) at
``a8c1dc581b9``, over non-test files with dunders excluded: the core package
declares **6,600** functions of which **259** carry ``@property``,
``@cached_property`` or a ``.setter`` / ``.getter`` / ``.deleter``;
``addons/base`` **2,394** and **31**. Small enough that nobody notices them, and
large enough to dominate a no-verb count in a single module. **Read every
no-verb figure in this section as excluding properties, or as not saying**
(§2.4.13).

* meaningless after reordering -- the qualifier was noise, drop it
  (``_get_related_assets`` → ``_get_assets``);
* unchanged in meaning, answering *whose* rather than *which* -- it is a
  namespace, leave it in front. **A leading noun that names a provider is a
  namespace, not a qualifier**: the test is whether the token could follow
  "which". *Which* port -- the effective one, so it moves; *which* font config --
  there is only one, and ``weasy`` says whose;
* reads and distinguishes -- reorder it, the ordinary case. Where the qualifier
  carried a real relation the name never wrote down, write the tail instead of
  deleting it: ``_get_related_bundle`` → ``_get_bundle_containing_path``.

Backlog ``[gate doc_restated_counts]``. The ``fields`` family is converted: the
census table counts the definitions and names that spell it head-first against
the few that spell it the other way. **The rule is general; the conversion
reached one family** -- across the other collection heads the census searches,
the tail-first count is the backlog. A name in it is a backlog item, not an open
question. Four cautions, every one of them about the measurement rather than the
rule: ``naming_vocabulary._COLLECTION_HEADS`` is a **search**, so a head absent
from it is measured by nothing; ``ids`` is deliberately absent, because
``_get_partner_ids`` names a **field** and the field-hook rule owns that
spelling; ``_HEADS_HEAD_FIRST`` requires a token *after* the head, so a trailing
qualifier alone flips the verdict -- ``_get_template_cache_keys`` scores ``tail``
while ``_get_template_cache_keys_minimal``, three lines away and in the same
family, scores ``head``; and the ``_get_domain_*`` family (§2.4.1) scores
``tail`` whenever its ``<what>`` ends in a head, though its order is fixed by the
prefix. **Read the tail-first count as a candidate population**, never as a list
of defects.

**Seven of the tail-first count are that fourth caution firing, and they are not
backlog** ``[review]``. ``_COLLECTION_HEADS`` spells ``domains`` and not
``domain``, so a name already head-first on ``domain`` scores tail whenever its
qualifier happens to end in another head: ``_get_domain_rotting_records`` on
``records``, ``_get_domain_attachments`` on ``attachments``,
``_get_domain_legacy_keys`` on ``keys``, with ``_get_domain_accessible_records``
and three overrides of the first. All seven were confirmed **by return** rather
than by name -- five annotated ``-> Domain``, one returning ``Domain`` through
``super()``, one a list of domain tuples -- and reordering any of them makes it
worse, since ``_get_attachments_domain`` is tail-first for what the method
actually returns. So the count is an overcount of seven, and §2.4.4's "a name in
it is a backlog item" is wrong for exactly these.

**And the obvious repair is not available, which is why the head is absent rather
than forgotten.** Adding ``domain`` to the tuple builds BOTH regexes, so
``_get_domain_x`` becomes head-first *and* every ``_get_x_domain`` becomes
tail-first -- and ``_get_*_domain`` is one of the commonest getter idioms in the
tree (``_get_last_sequence_domain`` ×10, ``_get_product_catalog_domain`` ×7,
``_get_l10n_latam_documents_domain`` ×6). Measured before proposing, as two head
tuples over **one fixed tree**, so what it establishes is the delta rather than
either absolute: the change moves head-first 131 → 273 and tail-first 177 →
**355**, declaring **186** new backlog items and reclassifying 328 names.

**Those two "before" figures name no POPULATION, which is a different fault from
naming no commit and has the opposite repair.** There are two head/tail counts
over this tree and the sentence does not say which it means:

========================================  ====  ====
Population                                head  tail
========================================  ====  ====
``census()`` -- model-class methods        131   173
``governed_definitions()`` -- the gate's   131   176
========================================  ====  ====

Same tree, same scan, different denominators: ``census()`` walks model classes,
while the gate's own population adds module-level functions and closures under an
addon's ``models/``/``wizard/``. **All three extra definitions are tail-first**,
which is exactly why the head-first **131** agrees with the census row nine lines
above and the tail-first figure does not. The census table states 173; the gate
sees 176; the quoted 177 is neither, and off by one from the gate's.

**A figure that names no population reads exactly like a stale one, and the two
have opposite repairs** -- a stale figure wants re-measuring, and this one wants a
denominator. Nothing on the page distinguishes them, which is why the first
diagnosis of this pair was that they anchored to no commit: the walk that produced
that reading was correct and the conclusion drawn from it was not. So either name
the population beside the number, or state only the delta -- which is what this
paragraph does, and which is immune to the question.

**The seven are a caveat
about how to READ the number, never a correction to bank** -- banking 170 would
require the scan change, and the scan change asserts a 186-item claim about a
shipped convention that nobody has argued. ``domain`` is absent from the tuple
because it cannot be added without settling ``_get_x_domain`` first.

**A name-shaped test cannot answer this, and the first pass proved it**
``[review]``. That pass asked whether the token after ``get_`` is a head in
singular or plural form and returned **twelve**; reading the bodies cut it to
seven. The five it wrongly excused are genuine backlog and every one reads like a
head-first name: ``_get_attachment_domains`` returns *domains* and so is
tail-first, ``_get_record_context_keys`` returns a ``list[str]`` of keys,
``_get_name_search_account_types`` returns types, ``get_model_options`` returns
options. §2.4.4 already says the head is a claim about the returned thing, so the
measurement has to read the return; the annotation settled seven of the twelve in
one line.

**The head noun is a type claim about the members** ``[review]``, and ``keys`` is
the one that hides it -- anything is a key of something, so the word survives
whatever the body returns. ``ir.ui.view``'s
``_get_cached_template_prefetched_keys`` returned ``["id", "key", "active"]`` and
its caller spent them as ``view[f]``: they are **field names**, and one of them
is a field *called* ``key``. It is ``_get_field_names_in_cached_template``. Ask
what a member **is** before choosing the head; where the head and the body
disagree, the reordering is the smaller half of the repair.

**And a singular head naming a mechanism claims that mechanism** ``[review]``.
``keys`` above is a collection head; the same test bites harder on a head naming
a thing with **behaviour** -- ``filter``, ``matcher``, ``resolver``, ``rule`` --
because such a word promises a callable or an object implementing one.
``http/routing.py``'s ``_get_endpoint_param_filter`` returned
``tuple[bool, frozenset[str], str]``: whether the endpoint takes ``**kwargs``,
the parameter names it declares, and what its first parameter is called. Those
are three facts a filter would need and not one of them is a filter -- the
filtering is done by a closure forty lines down, over these three values. It is
``_get_endpoint_param_acceptance``. **The head is a claim about the return's
type, never a summary of what the caller will do with it.**

**A leading noun that names a thing is a namespace; a stack of adjectives is a
qualifier** ``[review]``. This is the sharp form of the *which* test above, for
the case that test leaves open -- a leading run of two or more tokens. Ask
whether those tokens name something that exists in the system. A template cache,
an asset link, a record context and a client button all do, so
``_get_template_cache_keys``, ``_get_asset_link_urls``,
``_get_record_context_keys`` and ``_get_client_button_types`` keep their order
and are not backlog. *Cached template prefetched* and *root delegated* name
nothing -- they are adjectives stacked in front of a head, and they reorder.

**A qualifier that constrains the *input* does not reorder** ``[review]``.
Head-first moves a qualifier saying *which* of the returned things; it has
nothing to say about one that states a precondition on what the method was
handed. ``cli``'s ``get_single_database`` asserts a cardinality about the **list
it is given** and returns one database, so ``get_database_single`` would read as
a database that is somehow single. **Apply the test to the return, not to the
name.**

**A ``_by_<key>`` tail states the return is a mapping** ``[review]``, keyed on
what follows ``by``. The family is already here -- ``_get_model_names_by_table``,
``_get_models_by_module``, ``_get_field_names_by_model``,
``_get_records_by_value`` -- and it is where a head-first repair lands when the
method returns a lookup rather than a sequence: ``_get_template_views``,
returning ``{id_or_xmlid: view_or_exception}``, is ``_get_views_by_ref``.

**A ``_by_`` after a superlative is a criterion, not a key** ``[review]``. What
makes the rule above true is the head noun sitting directly on the ``by``:
``_get_records_by_value`` promises a mapping because ``records`` is what
precedes it. Where a superlative or a comparative intervenes, ``by`` names the
axis the comparison ran on and the return is whatever the head already said.
``http/controller.py``'s ``_get_classes_newest_by_identity`` deduplicates
controller classes on ``(module, qualname)`` keeping the newest, and returns a
``list[type]``: it is right. **A sweep has to be able to return "this one is
already correct"**, or the mapping rule turns every comparative tail into a
broken promise.

Three checks when renaming ``[review]``:

* **A body that reports what it did in one vocabulary and is named in another is a
  cheap place to look** -- ``_esbuild_circuit_record_failure`` logged
  ``circuit_open``, and is ``_open_esbuild_circuit``.
* **A ratcheted figure moving the wrong way is an objection.** That pair was first
  renamed to ``_run_esbuild``, breaking §2.4.9 in the commit that quotes it.
* **A rename is workspace-wide and a name is not unique.** A substitution on a
  short generic name cannot distinguish the owner. Prefer the name that is already
  qualified; where the substitution is unavoidable, run the *other* owner's
  callers first.
* **And verify a generic rename by its callers, not by its definition.** The
  bullet above prescribes the safer *substitution*; this is the check that it
  worked. Scoping a rename of ``lookup`` to the two files known to hold it left
  the one production caller behind -- ``envs.lookup(...)`` in
  ``orm/runtime/environment.py`` -- and nothing complained: the definition
  renamed cleanly and the module still imported. **A sweep fails loudly and a
  scoped substitution fails silently**, so having scoped one, grep the **old**
  name repository-wide and read every survivor. The failure mode is invisible
  from the file being edited, which is the file the author is looking at.

**Line the layers up: the odd name is found between layers, not inside one**
``[review]``. Where one operation appears at several layers, the name is fixed
by the family and not re-derived per layer -- and read alone, the odd member is
unobjectionable, which is why reading one layer never finds it.
``ConnectionPool`` carried ``close_database`` / ``close_all`` /
``drain_database`` / ``drain``, and *drain the pool* is a perfectly good name
for the fourth. It is wrong against the two layers above it, which spell the
same four symmetrically: ``EndpointRegistry.close_db`` / ``close_all`` /
``drain_db`` / ``drain_all``, and the module-level ``odoo.db`` four. It is
``drain_all``.

* **A delegating body whose verb differs from its callee's is the cheapest place
  to see it.** The four methods of ``EndpointRegistry`` are one loop each, and
  three of them read ``pool.close_all()``, ``pool.close_database(db_name)``,
  ``pool.drain_database(db_name)`` -- against one line reading ``pool.drain()``.
  **A wrapper that agrees with its callee everywhere but one line has found the
  defect for you.** It pays across packages too: ``release_`` is ``odoo/db``'s
  word for handing back one connection slot, and ``odoo/service`` had put it on a
  call that drains an entire pool and on another that closes a cursor --
  ``drain_swept_database`` and ``close_cron_cursor``.
* **The layer check proposes; §2.4.6's shadow test disposes** ``[review]``, and
  without that ordering this rule manufactures the very name §2.4.6 records
  ``cli/db.py`` manufacturing on purpose. ``ThreadedServer.reload`` is a one-line
  body calling ``lifecycle.restart()`` -- the tell exactly -- and lining the
  layers up spells it ``restart``, which would put ``self.restart()`` beside a
  bare ``restart()`` meaning the module function imported eleven lines above.
  **Where the aligned name shadows, the shadow wins**, and the two rules do not
  contradict each other so long as they are applied in that order.

**The second owner of a name can be in the same file** ``[review]``, and the
bullet above about substitutions assumes it is somewhere else. The sharper case
is a class wrapping a library object of the same shape: ``ConnectionPool.drain``
shadowed ``psycopg_pool.ConnectionPool.drain``, the very method its own
``_drain_pool_safely`` calls four lines away, so a substitution on ``.drain()``
in ``pool.py`` rewrites both the caller and the callee it delegates to.
**Where a class wraps a library object, check every bare verb against the
wrapped API -- before renaming, and before deciding a name is fine.** A name
that stutters against the thing it wraps is not merely unsearchable; it is the
one shape where the rename itself is dangerous.

**The member that already has a spelling is usually in the same file**
``[review]``. The namespace bullet above says to look for it; this is the
general form, and it is the cheapest evidence a head-first repair can have.
``schema.py``'s ``drop_depending_views`` sat ten lines above
``get_views_depending_on_table``, took the same ``(cr, table, column)``, and its
entire body is a loop over that function's return -- one noun phrase, two
orders, adjacent, with the right one already written down. It is
``drop_views_depending_on_table``. **Grep the file for the noun before choosing
an order**, and prefer the spelling a sibling already carries over the one the
rule would derive: a family that already contains a correct member does not need
the rule applied twice.

**The variable a method returns is the strongest evidence for its name**
``[review]``, stronger than the log line the first check points at: it was
written in the same body by the same author and it answers *what is this*, which
is the question the name has to answer. ``mrp.bom._bom_find`` assembled and
returned a local called ``bom_by_product``; the name it was owed was
``_get_bom_by_product``, spelled out in its own last line. A mapping's variable
is usually already head-first (``x_by_y``), so reading it settles the ordering at
the same time as the verb -- and where the variable and the name disagree about
the *shape*, the variable is the one the callers unpack.

**A first token repeating the model is what hides the verb** ``[review]``.
``_bom_find`` on ``mrp.bom``: the model qualifies every method it declares, so a
leading noun naming that same model buys nothing and costs the rule its foothold
-- ``classify`` partitions on the first token, so it scores ``bom``, which
carries no rule. Grepping a model's file for methods whose first token is the
model's own noun is the cheapest search for this defect, and it needs none of the
namespace weighing the general case needs: **a namespace that names one model is
not a namespace**, because it could not survive being moved to another.

2.4.5 Converters
~~~~~~~~~~~~~~~~

**``X_to_Y`` is the converter idiom, and ``to`` is the verb** ``[review]``. The
definitions spelled that way (census table) are most of them right: the name
is the pair of representations, and it buys the searchable families ``_str_to_*``
and ``_*_to_sql``. **``Y_from_X`` is the same idiom spelled backwards**, and
almost every ``_from_`` name is innocent -- the verb leads and *from X* is a source
qualifier. The offender is the shape with **no verb at all**:
``_db_id_from_xmlid`` beside ``_xmlid_to_record_id``, one operation both ways in
one class. Repair by reading the return, not by flipping the arrow.

Four limits:

* **A converter returns the representation its name promises**, so a strict-shape
  name annotated ``-> None`` is not one -- though not every such case is a defect
  (``mail``'s ``_thread_to_store`` serialises into an accumulator it is handed).
* **The idiom holds only while the conversion is total in one operand.** An
  operand that steers the result leaves no pair to name: ``_paperformat_to_css``,
  taking a landscape flag and template overrides, is ``_prepare_paperformat_css``.
* **Two representations of one value, not a value and the container it came
  from.** ``_mimetype_from_values(values)`` is fully determined by its argument and
  is still not a conversion -- the mimetype is guessed by a fallback chain. It is
  ``_get_mimetype_from_values``.
* **The receiver can supply the left operand.** A leading ``_to_`` is correct
  where the receiver is the source representation:
  ``attachment._to_http_stream()``.

**``convert_to_*`` is the field protocol and is reserved, not an ``X_to_Y``
spelled wrong** ``[review]``. ``Field.convert_to_cache``, ``convert_to_column``,
``convert_to_record``, ``convert_to_read``, ``convert_to_write`` and
``convert_to_export`` name one representation the *receiver* converts **into**,
the receiver being the field, and an override of one is bound by the ORM calling
it. Measured 2026-09-15 over the four repositories: ``convert`` leads **222**
definitions, **157** of which carry ``to``, and the protocol is most of them.
**So a leading ``_convert_`` is right only there.** Elsewhere it states the
operation twice -- ``X_to_Y`` already says a conversion happens -- and
``_convert_amount_to_company_currency`` is ``_amount_to_company_currency`` under
the idiom above, or a ``_get_`` where the second limit bites.

**``2`` is the ORM's cardinality notation and nothing else** ``[review]``. It is
reserved the way the table in §2.4.3 means it: ``many2one``, ``one2many``,
``x2many`` and the abbreviations built on them (``_m2o``, ``_o2m``, ``_x2many``)
are field-relation terms of art, and a name wearing one is right. Everywhere
else ``2`` is a converter spelled short, and the idiom is ``X_to_Y`` --
``date2datetime`` is ``_date_to_datetime``. *Frozen reading* (§1.4) at
``75ef0eec641``, an ad-hoc scanner: **45** definitions under ``addons/`` carry a
digit ``2`` between two letters, **33** of them the cardinality notation. The
remaining twelve are the family this rule names, and they are hard to find
precisely because ``_to_`` is what a search for a converter spells.

**A conditional tail is not the left operand** ``[review]``. ``X_to_Y`` names the
pair; ``to_Y_if_X`` names the target and files the source under a condition,
which reads as the hedge §2.4.4 sends to the tail and takes the name out of both
searchable families at once -- neither ``_null_to_*`` nor ``*_to_none`` finds it.
``http/geoip.py``'s ``_to_none_if_null`` unwraps the sentinel a null GeoIP record
returns from every attribute read, and both halves of the idiom hold: the
conversion is total in its one argument, and ``_GEOIP_NULL`` and ``None`` are two
representations of *absent* rather than a value and the container it came from.
It is ``_null_to_none``. **Where the condition IS the source representation,
write it on the left**; a genuine condition on a conversion that is otherwise
total is the second limit above, and splits the name rather than qualifying it.

**The leading ``_to_`` is licensed by the receiver, and a module-level function
has none** ``[review]``. The limit above admits ``attachment._to_http_stream()``
because the receiver **is** the source representation. At module level, or on a
class that is not that representation, nothing supplies the left operand and the
name states one half of a pair: ``cli/scaffold.py``'s ``_to_snake_case(s)`` and
``_to_pascal_case(s)`` are ``_str_to_snake_case`` and ``_str_to_pascal_case``,
joining the searchable family this section already names. **The blind spot is
that a leading ``_to_`` reads finished at every call site**, because the argument
sits beside it -- the same mechanism §2.4.6 gives for a trailing preposition,
running the other way.

2.4.6 Tails and operands
~~~~~~~~~~~~~~~~~~~~~~~~

* **In an addition, the tail names what is added, not the medium** ``[review]``.
  ``_add_header_footer_html`` ended in what it adds them *to*; it is
  ``_add_html_header_footer``. The signature settles it -- what a method adds is
  in its parameters, what it adds to is what it returns.
* **A verb that acts rather than returns still owes a noun** ``[review]``, naming
  what it acts on. An adjective is not a thing acted on (``_warn_stranded`` →
  ``_warn_stranded_sources``) and an adverb is less of one (``_reschedule_later``
  → ``_reschedule_job_later``): an adverb belongs in the tail, never in the
  object's place.

* **Except where the noun would shadow the callee** ``[review]``. This is the
  half that costs a reader something. ``cli/db.py``'s ``Db.drop``, ``duplicate``
  and ``rename`` each wrap a ``service.db`` function of the very name the rule
  would give them, so ``self._drop_database(args)`` would sit four lines from
  ``drop_database(target)`` meaning something else -- §2.4.4's unsubstitutable
  name, manufactured on purpose. ``Db.list`` is the same test with the sign
  flipped: there the *existing* name was the shadow, of a builtin the class
  annotates with, so it moved to ``list_databases``. **Ask which spelling
  shadows, not whether a noun is missing.**
* **And except where the method name is the word a user types** ``[review]``.
  A subcommand handler reached by ``set_defaults(func=...)`` is free to rename
  as *code* (§2.4.14), and in ``cli/db.py`` it should not be: ``Db.init`` /
  ``load`` / ``dump`` are ``odoo-bin db init`` / ``load`` / ``dump``, and
  ``_add_init_parser`` binds the same word a third time. **This is §2.4.14's
  third category, not its first** -- the name is written down in shell history,
  in runbooks and in other people's scripts, none of which this workspace can
  rewrite, and it is invisible to every grep because the caller is a human. A
  *private* handler makes no such claim, which is the whole difference:
  ``Module._install`` installs **the modules named on the command line** and is
  ``_install_modules``, ``I18n._import`` moves translations and is
  ``_import_translations``.
* **Do not read either exception as "the receiver implies the object"**
  ``[review]``. That is broader than both and would take a convention wholesale.
  ``modules/loading.py``'s ``_PackageLoader`` holds one package and writes the
  object in every one of its stage methods -- ``import_python_module``,
  ``load_models``, ``log_cost`` (``report_cost`` until ``a13f69bf0c81``) --
  and is right to: the receiver is an **agent**, not the object, so *package
  loader import python module* is not a stutter the way *db drop database* is.
  Where a class is agent-shaped and the siblings already write the object, a
  bare verb is the odd one out and owes its noun like any other: ``announce``, ``mark_loaded`` and ``stamp_installed`` were
  that class's three exceptions and are ``announce_module``,
  ``mark_module_loaded`` and ``mark_module_installed``.
* **A preposition at the end of a name is an operand the author meant to write**
  ``[review]``. ``_get_stream_from(record, ...)`` reads as finished because the
  argument supplies the noun at every call site, while a search, an override list
  and a stack trace all show the name alone. **Repair it by writing the operand,
  not by deleting the preposition** -- the preposition carries the axis the family
  varies on, so ``_get_stream_from_record`` and ``_get_stream_placeholder`` leave
  ``_get_stream_`` finding every producer and nothing else.
* **A family whose members differ only in the preposition has written the axis
  and left out every value on it** ``[review]``. The rule above reaches one
  method at a time and reads as a tidy-up; a *family* is where it stops being
  one. ``odoo/db``'s endpoint registry carried three pairs --
  ``get_maxconn_at`` / ``get_maxconn_for``, and the same for the budget and the
  pool -- beside a ``get_endpoint_of``. Every name is finished at its call site
  and none is finished in a traceback, and the overload is not decoration: ``at``
  takes a resolved endpoint, ``for`` takes the ``readonly`` flag the endpoint is
  resolved *from*. Writing the operand states that -- ``get_maxconn_at_endpoint``
  against ``get_maxconn_for_readonly`` -- and the pairs then read as the two
  layers they are. **A family is the evidence that the preposition was carrying a
  type, so write the operands together or the surviving one re-reads as noise.**
* **A distributive tail is the plural of the operand, never ``_each``**
  ``[review]``. ``_close_each(pools)`` and ``_drain_each(pools)`` name the
  iteration, which every method over a sequence does, and leave the object to the
  parameter; they are ``_close_pools`` and ``_drain_pools``. The same reading
  retires ``forget_each(keys)`` in favour of ``forget_keys``. Where a singular
  neighbour exists the plural is the whole distinction and there is nothing left
  for ``_each`` to say.
* **Where two neighbours return different representations, the tail says which**
  ``[review]``: ``_get_stream_placeholder`` returns a ``Stream``,
  ``_get_placeholder_bytes`` returns bytes from the same default path.
* **A predicate is named for the question, in the tense the caller asks it**
  ``[review]``. ``_is_tls_verified`` reads as settled state where the caller is
  asking a prospective question.
* **A predicate named for the branch its caller takes is named for the wrong
  subject** ``[review]``. ``_skip_bom_line(product)`` returns a ``bool`` and skips
  nothing -- skipping is what the caller does with the answer. Ask the question
  about the subject and leave the caller its verb: ``_is_bom_line_skipped``. This
  is worse than the ``_should_`` family §2.4.8 parks, which at least announces
  that a question is being asked; an imperative reads as an instruction, so ``if
  line._skip_bom_line(product):`` parses as a statement with a stray ``if`` and
  the reader has to reach the body to learn it returns anything at all.
* **The receiver can supply the noun the verb owes.** The rule two bullets up
  asks for a thing acted on, and on a recordset method ``self`` *is* it:
  ``_post_inventory`` and ``_action_cancel`` owe nothing further. The tail is
  owed where the object is not the receiver (``_warn_stranded_sources``), or
  where the verb reaches one named part of it (``_update_cost_mode``).

* **``_each`` is one word of a family; any tail naming *how* the members were
  chosen sits in the object's place too** ``[review]``. The rule above retires
  ``_close_each`` and ``forget_each``; the same reading retires the tails that
  look less like placeholders because they say something true.
  ``ReachabilityProbe.forget_matching(predicate)`` stands beside
  ``forget(key)``, ``forget_keys(keys)`` and ``forget_all()`` -- three siblings
  that write the operand and one that spends its tail on the selection instead;
  it is ``forget_keys_matching``. ``IdlePoolReaper.close_in_background(target,
  pools, name)`` spends its tail on *where the work runs*, beside a
  ``_close_pools(pools, scope)`` that already settled the object; it is
  ``close_pools_in_background``. **A tail says which, how or where; none of the
  three is the object, and the object is still owed.**
* **A temporal clause is a modality wearing a different part of speech**
  ``[review]``. §2.4.4 sends a leading *safe* or *maybe* to the tail as a
  condition; this is the case with no modality word at all, where a phrase
  saying **when the method is called** stands in for the object.
  ``ConnectionPool._reap_after_return`` was a ``try``/``except`` around
  ``_reap_idle_pools_if_due``, and *after return* is answered by both its call
  sites, which are inside ``give_back``. What it actually adds is the swallow,
  which its own siblings ``_close_pool_safely`` and ``_drain_pool_safely`` had
  already spelled: it is ``_reap_idle_pools_safely``. **A wrapper that differs
  from its callee only by swallowing takes the callee's name plus the modality**
  (§2.4.10's wrapper rule, with the tail §2.4.4 prescribes) -- naming it for the
  call site states what the call site already says, and states it once per
  caller.

* **``_by_<key>`` has two senses and only one of them is §2.4.4's rule**
  ``[review]``. That tail states the return **is** a mapping keyed on ``<key>``;
  in ordinary English it also means *addressed by*, and the second sense passes
  review unchallenged precisely because it reads correctly.
  ``cli/module.py``'s ``_get_modules_by_name`` returned a **recordset** and
  ``cli/populate.py``'s ``populate_models_by_name`` returned **None**; both are
  the second sense, and are ``_get_modules_named`` and ``_populate_models_named``.
  The same file carried the first sense with no tail at all --
  ``_prepare_model_factors`` returns ``dict[model_name, factor]`` and is
  ``_prepare_factors_by_model_name``. **The test is the return, never the
  argument**, and a file holding both senses is where the ambiguity finally costs
  something.

2.4.7 Payload against read
~~~~~~~~~~~~~~~~~~~~~~~~~~

**``_get_`` is not a default.** It is 23.8 % of every method in this repository's
model layer (the census table has the count), having absorbed reading, building,
deriving and computing. The split that matters is against ``_prepare_``: 701
definitions are payload builders -- they end in ``_vals``, ``_values``, ``_data``,
``_dict``, ``_context``, ``_defaults``, ``_list``, ``_args`` or ``_params`` -- yet
are spelled ``get_*``, against 911 already spelled ``_prepare_*``.

**Resolve it on the consumer, always** ``[review]``. Where the return value goes
is visible at the call site; whether a value was "already there" is a question
about the method's insides that two readers answer differently.

* feeds ``create()`` / ``write()`` / ``Command`` → ``_prepare_*``, whatever its
  provenance;
* feeds a **named non-ORM consumer** → ``_prepare_*`` too, naming the consumer
  rather than the shape: ``_prepare_eval_context``, not ``_prepare_eval_vals``;
* returns to a caller that merely reads it → ``_get_*``.

The test is the **mapping handed to** ``create()`` / ``write()`` / ``Command``,
not any value a caller happens to store. *Provisional in one direction only*: the
first bullet is settled, but moving the ``safe_eval`` / ``SQL`` /
rendering-context family onto ``_prepare_`` is not, because several of those names
are fixed by a binding (§2.4.14) -- ``_get_report_values`` is the clearest. Name
new ones this way; do not rename the bound ones.

* **Provenance is the tiebreak, and it separates artifacts from arithmetic**
  ``[review]``. An SVG or a block of bytes is an artifact, built to be handed
  over; a scalar that is the *answer to a question* is a read whatever arithmetic
  produced it. A question is ``_get_``, a thing is ``_prepare_``.
* **The payload suffixes are a search, not a verdict** ``[review]``. Most of what
  they find in ``base`` is correctly ``_get_`` -- ``_get_action_dict`` returns
  ``read()``'s output. Run the consumer test on every hit.
* **That it read acceptably is not a defence, and it is the objection to expect**
  ``[review]``. ``Report.barcode("QR", value)`` parses as English because
  ``barcode`` is a noun a reader silently verbs; it is ``prepare_barcode``.
* **A shape suffix on an extension point is a claim every override has to keep**
  ``[review]``. ``_get_installed_addons_list`` returned a ``frozenset`` while its
  override point returned a ``list``; head-first drops the suffix in one move,
  ``_get_addons_installed``.
* **A payload builder is often named for the operation it feeds, and that verb
  belongs to its caller** ``[review]``. ``_reflect_model_params`` returns the
  ``ir_model`` column values ``_reflect_models`` consumes: it is
  ``_prepare_model_vals``. **Ask whether the name already belongs to a method one
  frame up.**
* **A canonical verb can be wrong too** ``[review]``.
  ``_prepare_local_attachments`` migrated remote attachments and returned the
  local ones -- a write, then a filter, with no consumer anywhere. It is
  ``_migrate_attachments_to_local``.
* **A domain is not a payload, whatever verb assembled it** ``[gate naming]``.
  A domain is handed to ``search()``, never to ``create()``, so ``_prepare_``
  claims the wrong row for it, and the §2.4 table spells the free-standing
  form ``_get_domain_<what>``: ``_prepare_po_get_domain`` is ``_get_domain_po``,
  ``_prepare_badges_domain`` is ``_get_domain_badges``. ``classify()`` already
  routed every abolished verb with a ``_domain`` tail there; it now routes
  ``prepare`` the same way. *Frozen reading* (§1.4) at odoo ``5d1a36d538ac``,
  before the renames: **4** in ``addons/``, **5** in ``enterprise``, **1** in
  ``agromarin``, all renamed ahead of the rule so no floor moved for it.

**``_generate_`` is the largest member of the payload family and is not in the
table** ``[review]``. The four verbs the Payload row abolishes are a small family
between them; ``_generate_`` alone is far larger (census table). It carries two
meanings -- ``_generate_access_token`` builds a value and takes the payload
canonical, while ``mrp.unbuild``'s ``_generate_consume_moves`` **created records**
and took the domain operation's name -- it and its three siblings are
``_create_consume_moves``, ``_create_produce_moves``,
``_create_move_from_bom_line`` and ``_create_move_from_existing_move``, each a
body that is one ``create()`` -- so wiring the verb into ``ABOLISHED`` would turn
a gate held at a hard zero red across the whole family, and is owed its own
record. The rename does not wait for the record; the rule does.

**The payload suffix chooses an assemble verb's canonical, not its reach**
``[review]``. ``naming_vocabulary.py`` used to report one only when the name also
ended in a payload suffix, which is a reach test, and the four verbs are
abolished unconditionally -- so the gate read zero while the tree wore them.
*Frozen reading* (§1.4) at ``042da509ff66``: **21** model methods across the four
repositories opened with one of the four and the ratchet flagged **0** of them --
16 in ``addons/``, 2 in ``enterprise``, 3 in ``agromarin``, and **0** in the core
package, which had been swept by hand for exactly this reason. ``classify`` now
runs the consumer test above instead: ``_prepare_`` where the name carries a
payload suffix, ``_get_`` where it does not. **0** model methods open with one of
those four verbs and the ratchet flags **0**; the two figures are one
measurement, and a gap between them is the defect this paragraph used to record.

* **A reach test written as a canonical test is the shape to look for**
  ``[review]``, because it fails silently in the direction nobody checks: the
  gate goes on reporting, its floor goes on holding at zero, and what it has
  stopped looking at leaves no trace in either number. The suffix list was
  never wrong about *which* canonical to suggest -- it was answering a question
  it had not been asked.
* The gap hid two things beyond its own size -- the suffix list is short, and
  *object construction takes ``_prepare_`` too*, a factory having a consumer
  like anything else.
* **The three verbs the Payload row does not print stay a core-only reading**
  ``[review]``. ``naming_core_vocabulary.ASSEMBLE`` adds ``assemble``, ``craft``
  and ``forge`` on §2.4.20's argument that a row's printed entry can drain to
  zero while the operation continues under a word nobody listed. Their addon-side
  population is **0** in all four repositories, so promoting them to the shared
  ``ABOLISHED`` is free of renames whenever that reading is taken; it is not
  taken here, because the shared table moving would make the core gate's own
  branch unreachable.
* **A bare assemble verb is still out of scope for this gate.** ``classify``
  partitions on the first token and returns nothing when there is no remainder,
  so ``make()`` and ``_build()`` are reported by the core gate alone (§2.4.6) --
  and, since ``5b01cd9535ac``, so is every other bare verb the core gate's body
  rules reach: ``classify_definition`` used to return on a bare name before any
  body rule ran, so ``def _resolve(settings)`` that always produced one passed a
  gate whose own ``resolve-total`` rule names it.

**``_calculate_`` is the read family's ``_generate_``**
``[gate doc_restated_counts]``. It names the arithmetic where ``_generate_`` names
the manufacture, and unlike ``_generate_`` it is owed no record, because the
Provenance bullet above has already settled it: a scalar that answers a question
is ``_get_`` whatever produced it. The census table counts the model methods that
still wear it. Two cautions from draining it out of ``mrp``:

* **The rename collides, and the collision is the finding.** Three of them
  derived one field, ``duration_expected``, alongside a ``_get_duration_expected``
  that was already there -- which is *Naming standardization is instrumental*'s
  argument, running inside a single file. Give each the tail that says which
  derivation it is (``_get_duration_expected`` from the operation,
  ``_get_duration_expected_from_dates`` from a span) rather than dropping the one
  that renamed second.
* **A stale name is stale in its noun as well as its verb.**
  ``_calculate_date_finished`` returned the value of the field this fork calls
  ``date_end``; renaming only the verb leaves the name pointing at a field that
  no longer exists.

**Between ``_prepare_`` and ``_update_``, ask who owns the mapping** ``[review]``.
Both hand back a ``dict`` and the consumer test cannot separate them, because the
consumer is the same one. The **parameter list** separates them: a method that
assembles the mapping is ``_prepare_``; a method handed a mapping its caller
already owns, which adds to it, is the Mutation row (§2.4.12) even though nothing
ORM is written. ``_set_replenish_data(new_lines, product, replenish_data)`` is
``_update_replenish_data``. **Returning the mapping it was handed does not make
it a builder** -- a caller writing ``data = obj._update_data(..., data)`` is
rebinding a name, not receiving a new object.

Backlog (census table): the ``_prepare_*`` definitions that call ``create()``,
``write()`` or ``unlink()`` in their own body. A candidate population -- only a
builder whose **return value** is not the mapping it assembles is in the wrong
family.

**A read verb may not hide a write** ``[review]``. Both rows above discriminate
on where the return value *goes*, so neither has anything to say about a getter
that also changes something on the way. ``cli/module.py``'s
``_get_module_model`` returned ``env["ir.module.module"]`` -- after calling
``update_list()`` on it, which rewrites the module table from what is on disk.
Every caller read the name as an accessor and none could see that asking for the
model was what refreshed it. Name the write: it is ``_sync_module_list``
(§2.4.12), and returning the model it converged is fine.

* **The test is whether a caller who did not want the write can avoid it.** A
  memo is exempt for that reason -- it changes *when* a body runs and nothing a
  caller can observe (§2.4.10) -- and so is a lazy attribute the getter fills on
  first use. A write to the database, the filesystem or another object's state
  is not.
* **A side effect nobody named is how one operation ends up with two owners.**
  ``update_list()`` ran once per subcommand because each happened to call one
  getter once; that invariant lived nowhere but in the call graph.
* **Where the write and the return are one decision, neither verb is honest**
  ``[review]``. The repair above moves the name onto the write
  (``_sync_module_list``) and lets the return ride along, which works because
  there the write *is* the operation. It does not reach a method that decides
  something, installs the consequence on the receiver, and hands the rest back:
  naming that for the read hides the write, and naming it for the write hides
  the return its caller is built around. ``http/_serve.py``'s
  ``_get_serve_target_and_mode`` matched the path, set ``self.dispatcher`` on
  both branches -- read four frames away in the application's error path, never
  by its own caller -- and returned the bound serve callable with its
  ``readonly`` flag. What is owed is a verb making **no promise about the absence
  of a write**: ``_select_serve_target_and_mode``. **A choice that is made rather
  than reported may be installed; a read may not.**
* **Importing a Python file is a write, and a read verb hides it the same way**
  ``[review]``. The example above is a database write; the cheaper miss is module
  execution. ``cli/upgrade_code.py``'s ``get_upgrade_code_scripts`` (the upstream
  source rewriter, since deleted) reached ``_load_module_from_file`` for every
  script in the version range, which imports and **runs** each one, so asking
  for the scripts was what executed their module bodies -- and no caller reading
  ``get_`` could see it. §2.4.3 reserves ``_load_`` for the ORM operation and for
  module loading, and this was the second of those: it became
  ``load_upgrade_code_scripts``. **A reserved verb is owed where it applies, not
  merely permitted.**

2.4.8 Predicates and validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**A ``bool`` return does not make a predicate** ``[review]``. **336** functions in
this repository are annotated ``-> bool`` and are not predicates, against **313**
that are: ``write`` and ``unlink`` return ``True`` by ORM convention, and
``_coerce_bool(value, default)`` is a converter. Ask what the boolean *is* -- an
**answer** to a question about the subject is a predicate, a **converted value**
keeps its conversion verb, a **conventional acknowledgement** is nothing at all.
The call site is the tell: a predicate reads naturally inside an ``if``, a
converter where a type would.

**That pair of figures is measured over a different population from the ones
above it** ``[review]``, and nothing in either sentence says so. ``census()``
counts methods on ``is_model_class`` nodes, but this pair comes from
``_bool_annotated``, which sits **outside** that walk and returns the *union* of
two populations: functions declared at **module level**, plus methods on model
classes. So the denominator here is wider than §2.4.3's by every module-level
function, and a reader comparing the two as though they shared a scope is
comparing different trees. **Re-derive it rather than trusting a remembered
shape**: it reads ``tree.body`` and the direct body of each model class, so a
**nested** function is invisible to it, and so is every method on a **plain
class** -- the population §2.4.13 already names as counted by nothing, and which
this figure does not quietly rescue.

**Three scopes appear in this one section, and no two are the same tree**
``[review]``. §2.4.3's figures count **model methods, repository-wide**; the pair
above counts **module-level functions plus model-class methods, direct children
only, repository-wide**; and the frozen reading further down counts **every
function that is neither a property nor a dunder, in the core package alone**.
Each states its own rule where it stands, so none misleads by itself -- but they
are stacked within a page of each other and a reader who carries a number from
one to another is comparing different trees. **Read the scope before comparing
two figures in this section**, and expect the answer to differ on both axes: what
counts as a definition, and which tree it was counted over.

**A name can fail both halves at once, and then no count in this section can see
it** ``[review]``. ``module_graph.py``'s ``not_in_the_same_phase`` is annotated
``-> bool`` and is a predicate spelled as a negation, so §2.4.3 and the paragraph
above both have an opinion about it -- and it is declared *inside*
``ModuleNode.phase``, on a class that is not a model, so it is out of scope for
the module-level half and out of scope for the model-class half. Renaming it
moves no figure and trips no ratchet. This is §2.4.13's "a file can be sixteen
names wrong and green" with a name pointed at rather than a population described:
**where the two halves of the union do not overlap, they leave a hole, and every
nested definition in the repository sits in it.**

**And the converse: the prefix is a claim about the return type, so a predicate
that does not return a ``bool`` is lying about a value the caller can see**
``[review]``. The first rule keeps a ``bool`` from conferring the prefix; this
one keeps the prefix from surviving where the ``bool`` went away. It is the more
expensive direction, because a three-valued answer *degrades* to a true one and
the name goes on working: ``db/schema.py``'s ``has_unaccent`` returns a
``FunctionStatus`` of ``MISSING`` / ``PRESENT`` / ``INDEXABLE``, and its callers
split both ways -- ``if not registry.has_unaccent`` reads the truthiness, while
``== FunctionStatus.INDEXABLE`` reads the third value the name denies exists.
**Name the value, not the question**: ``get_unaccent_status``. Two consequences
worth having:

* **A degrading return is why nothing catches this.** An ``Enum`` whose zero
  member is the negative case answers every ``if`` correctly, so no test fails
  and no annotation disagrees with a call site; only reading the return type
  against the prefix finds it.
* **The rename does not travel by itself.** The function is one name; the value
  it feeds may be another. Here ``registry.has_unaccent`` holds the same
  ``FunctionStatus`` under the same wrong prefix and reaches the browser as a
  key in the session dict, which makes *that* half a wire-format change under
  §2.4.14 -- owed a record and a rewrite of every repository, not a sweep.
  **Rename the half that is inside the workspace and say which half you left**,
  rather than leaving both because one of them is expensive.

**Validation raises; predicates return.** ``_check_*`` is canonical and matches
``@api.constrains``. On model classes ``_validate_``, ``_verify_``, ``_ensure_``
and ``_control_`` are gone (the census table holds their zeros) -- they were one
operation under four names, all four verbs are abolished (§2.4.3), the
``naming`` floor is a hard 0, and the sweep reached them. A method that
*answers* rather than enforces is ``_is_*`` / ``_has_*`` / ``_can_*`` and must
not raise.

**Those two zeros are a scope, not an extinction** ``[review]``. ``census()``
builds its population from ``is_model_class`` nodes only, so they say that no
*model method* wears these verbs -- never that none survives. The four verbs are
still defined outside that scope, on plain classes and at module level, and
every one of those is invisible to the gate for the reason §2.4.13 gives. A
reader who takes the zeros at face value concludes the family is extinct while
it is merely unmeasured. **Read a zero from this census as "none that the scope
can see"**, and re-derive the population rather than quoting a size for it --
this one is not gated, so any figure written here would drift unchecked.

* **A predicate prefix is a contract, and a raising body breaks it** ``[review]``,
  with nothing enforcing that direction. ``_can_execute_action_on_records``
  returned ``None`` and raised ``AccessError``, so ``if not action._can_…():
  return`` guarded exactly when access was **granted**; it is
  ``_check_access_to_run``.
* **A predicate may log** ``[review]``. **The tell that reporting has become the
  contract is a parameter only the log reads.** That tell needs a verdict, or two
  readers find it and disagree: **the predicate prefix still wins.**
  ``ir.cron``'s ``_is_user_archived(job, env)`` reads ``job`` for nothing but the
  ``cron_name`` in its warning, and it is still a predicate, because the answer
  is the return and the report is a side effect no caller can observe. ``_warn_*``
  is for a body with **no answer to give** (``warn_running_as_root`` below).
  What the log-only parameter actually tells you is that the predicate is not
  reusable as a pure question -- a note for whoever next wants to ask it from
  somewhere that must not log, not a reason to change the verb.
* **A body that answers and consumes in one call is not a predicate; it is an
  acquisition, and the canonical is ``acquire_*``** ``[review]``. Every
  rate-limited operation in the tree needs *may I, and if so nobody else until
  the interval elapses*, which returns a ``bool`` and **writes** the timestamp
  that makes the next answer ``False``. ``odoo/db`` grew three of them
  independently and spelled all three as questions -- ``IdlePoolReaper.due()``,
  ``ReplicaLagGate.due_for_sample()`` and ``CheckoutTracker.due_for_report()``,
  each stamping its own ``_last_*`` under a lock -- which is precisely the
  duplicate report §2.4.3 exists to produce, and it stayed invisible because
  three spellings of one operation cannot be greped into one place. They are
  ``acquire_check_interval``, ``acquire_sample_interval`` and
  ``acquire_report_interval``. Three notes:

  - **The verb is not new.** ``ConnectionBudget.acquire`` in the same package is
    the same contract over a slot rather than an interval, and §2.4.18's warning
    against inventing a verb is the reason to take the one already there.
  - **The tell is a ``_last_*`` write, not the lock.** A predicate may take a
    lock to read consistently; it may not leave the object different.
  - **``_is_*`` survives beside it for the half that only asks.**
    ``IdlePoolReaper.probably_due`` is the lock-free pre-check the same class
    runs before the acquisition, mutates nothing, and is ``is_probably_due``. A
    class that has both should keep both: the pair *is* the design.
* **A ``_check_`` bound to ``@api.constrains`` that never raises cannot be
  repaired by renaming** ``[review]``. Either it is a constraint and owes a
  ``ValidationError``, or it is advisory and owes a ``_warn_*`` helper called from
  ``create`` and ``write`` -- a behavioural call. **Read every
  ``@api.constrains`` hook you meet for a ``raise``.**
* **The three predicate prefixes are reserved** in the sense the reserved-verb
  table means it.
* **Unbound, the same prefix hides a different family altogether.**
  ``_check_contents(values) -> values`` returned the dict ``create`` hands to
  ``super()``; it is ``_prepare_contents``. The wrong prefix costs placement too,
  since §2.2's table is keyed on it. A ``_check_*`` that is not an
  ``@api.constrains`` hook belongs beside the operation it guards.
* **A third kind is neither, and the rule above must not be read onto it**
  ``[review]``: an ``@api.constrains`` hook whose body is ``pass``, declared so
  that a downstream module has a constraint to override. ``hr.employee``'s
  ``_check_ssnid`` is empty and ``l10n_us_hr_payroll`` supplies the ``raise``.
  It owes no ``ValidationError`` here and it is not advisory -- it is an
  extension point, and the ``@api.constrains`` is what registers the trigger
  fields on behalf of every overrider, which is why the declaration cannot move
  downstream with the body. **The test is whether an override exists**, not what
  the body does: an empty constraint nobody overrides is dead, and the repair
  there is deletion rather than either branch above.

**``_should_`` is a fourth predicate prefix, and the row does not list it**
``[gate naming]``. *Frozen reading* (§1.4) at ``216b5a03021``: ``_is_`` **363**,
``_has_`` **70**, ``_can_`` **69**, against ``_should_`` **58**, ``_must_`` **8**,
``_needs_`` **6** and ``_requires_`` **1**. The canonical is the three: ask the
question in the tense the caller asks it and put the modality in the tail
(``_should_stream_upload`` → ``_is_stream_upload_required``).

* **The necessity modals are in ``ABOLISHED`` now** -- ``should``, ``need``,
  ``needs``, ``must``, ``want``, ``wants``, ``requires`` -- and the entry prints
  ``_is_`` because a table entry prints one canonical, not because the family
  has one. The printed target is the hypothesis §2.4.8 already says every
  canonical is: ``_need_special_rules`` is ``_has_special_rules``, and
  ``_wants_multi_company_group``, which returned ``True``, ``False`` or ``None``
  meaning *no change*, is §2.4.11's ``_resolve_multi_company_group_membership``
  -- a name no predicate prefix could carry honestly. What the entry settles is
  that the name is reported at all: ``mrp`` drained its eight by hand while the
  gate read the addon as clean, which is the shape the table exists to close.
  *Frozen reading* (§1.4) at the commit that landed it: **42** in ``addons/``,
  **11** in ``enterprise``, **7** in ``agromarin``. The shared table also
  reaches ``naming_core_vocabulary``, and its whole core-side population was
  three names (``web``'s ``_should_captcha_login``, ``sale``'s
  ``_should_show_product``, ``tools/populate``'s ``field_needs_variation``),
  renamed in the same commit so no hard zero moved.
* **Possibility stays out of the table**, for the reason the next paragraph
  gives: ``may`` / ``might`` / ``could`` already have ``_can_`` and the repair is
  a reordering the gate cannot print.

**A possibility modal already has a canonical prefix, and then the repair is a
reordering rather than a rewrite** ``[review]``. The rule above is written for
*necessity* -- ``_should_``, ``_must_``, ``_needs_``, ``_requires_`` -- where the
modality has no prefix of its own and genuinely has to be rewritten into the
tail. Applied literally to *possibility* it damages names that are one move from
right: ``_groupby_spec_might_duplicate_rows`` would become
``_is_row_duplication_possible``, which invents a noun and drops the subject.
``_can_`` **is** the possibility modality and is already one of the three, so
``may`` / ``might`` / ``could`` promote the prefix to the front and keep every
other word -- ``_can_groupby_spec_duplicate_rows``,
``_can_cache_value_hold_new_ids``. **No word is invented and none is lost, which
is the tell that the ordering was the whole defect.** The two directions are not
symmetric: necessity keeps the rewrite
(``_read_group_aggregates_need_dedup`` → ``_read_group_is_dedup_required``),
because there is no ``_needs_`` prefix to promote.

**A predicate spelled as a statement or an imperative is the same defect as one
with no prefix at all** ``[review]``. The three prefixes ask a question; a
third-person verb *asserts* one and an imperative *orders* one, and both grammars
promise that the method acts. A sweep of ``odoo/http`` found four in one package:
``_hide_exception_internals()`` hid nothing -- it answered whether the traceback
reaches the client; ``_hands_over_to_the_debugger()``,
``_dbfilter_reads_the_host()`` and ``suppresses_uncommitted_warning()`` each
stated a fact about the subject in the grammar of an action. The repair is the
move the ``_should_`` bullet already prescribes -- ask the question and put the
rest in the tail: ``_is_exception_detail_hidden``,
``_is_debugger_handover_required``, ``_has_host_placeholder`` and
``is_uncommitted_warning_suppressed``.

* **The call site is the tell.** ``if not _hide_exception_internals():`` reads as
  a guard against an action that never happens, and a reader who trusts the
  grammar has the condition backwards.
* **A fourth was found by the same sweep, and no package-scoped sweep could have
  reached it** ``[review]``. ``suppresses_uncommitted_warning`` is the identical
  defect -- a third-person verb asserting a fact about the subject, read at a
  call site as ``if participant is not None and participant.<name>()`` -- and it
  is a ``typing.Protocol`` member **declared in ``odoo/service/transaction.py``**
  which ``odoo/http`` merely implements. A sweep scoped to a package reads
  implementations and never declarations, so the name sat inside the swept files
  and outside the swept scope. It is ``is_uncommitted_warning_suppressed``, moved
  with its declaration, its one caller, its implementation and two test fakes in
  a single change (§2.4.14). **A package is not a closed scope for naming**: read
  the declaration site of every ``Protocol`` a package implements before calling
  that package swept.
* **A third-person verb is a defect only where the subject is not the receiver**
  ``[review]``, and the unqualified reading of this rule condemns names that are
  right. ``addons/base`` holds ``FromFilter.matches(email_from)``,
  ``AttachmentStorage.owns_key(key)`` and ``_fits_column(field, parsed)``, and
  ``from_filter.is_email_matched(email)`` is worse than what it replaces: the
  receiver **is** the subject, the sentence is complete at the call site, and the
  prefix only stutters. Against them, ``res.users``'
  ``_escapes_own_record(vals)`` and ``_settings_value_is_a_choice(name, value)``
  put the subject in the **parameter list** and leave the receiver as an agent
  (§2.4.6), so the sentence reads as something the receiver does. **Ask where the
  subject is before rewriting the grammar.**
* **The second discriminator is stative against dynamic** ``[review]``, and it is
  the one that decides when the receiver is the subject anyway. *Match*, *own*,
  *fit*, *contain* and *support* name a relation that holds; *render*, *combine*,
  *change*, *absorb*, *escape* and *fail* name an event, and a name for an event
  promises the method causes it. **The test is the progressive**: *is rendering*
  is natural and *is matching* is not, so ``ir.actions.report``'s
  ``_renders_pdf()`` -- which answers whether rendering is switched on at all --
  is ``_is_pdf_rendering_enabled``, while ``matches`` stays. A name can fail both
  discriminators, and then it is not a marginal call.
* **The larger half of this family has no part of speech at all** ``[review]``,
  which is why it survives a sweep looking for verbs. ``addons/base`` carried a
  past participle (``_all_branches_selected``, ``_any_capacity_declared``), an
  adjective (``_jsonable``, ``_auto_install_dependencies_satisfiable``), a
  prepositional phrase (``_on_login_cooldown``) and an adjective phrase
  (``_rpc_api_keys_only``) -- seven names, none of which a grep for a wrong verb
  can reach. **And the subject-first sentence is the same family wearing the verb
  in the middle**: ``_addon_is_present`` and ``_arch_is_absent`` contain ``is``
  and still do not lead with it, so they are invisible to a ``_is_`` grep *and*
  to ``classify``'s first-token partition at once. The argument for moving the
  prefix to the front is not grammar, it is §2.4.3's: one spelling per operation,
  so that the family can be found.
* **A predicate prefix over a body that returns nothing is not a weakened claim
  but an inverted one** ``[gate naming_core]``. The rules above keep a ``bool``
  from conferring the prefix and keep the prefix from surviving a degrading
  return (``has_unaccent``); the third case is the prefix surviving where there
  is **no return at all**, and then the caller reads a question and gets a
  write. ``naming_core_vocabulary``'s ``predicate-no-return`` kind reports an
  ``_is_`` / ``_has_`` / ``_can_`` over a body with no return and no raise, and
  its ``preposition-predicate`` kind reads the prepositional-phrase row above
  the other way -- a first token ``in`` / ``within`` / ``on`` / ``at`` /
  ``under`` over a body that answers a question is ``_is_`` / ``_has_``
  (``ddl._in_code_ranges`` → ``_is_within_code_ranges``), a ``@property`` being
  exempt. Both read 0 in core and in every governed addon scope when they
  landed (``5b01cd9535ac``).
  ``NameManager.has_field(node, name, node_info, info) -> None`` **records** a
  field as available -- it updates ``available_fields``, assigns ``field_groups``
  and calls ``available_names.add`` -- and ``ir.ui.view``'s
  ``_has_calendar_fields`` one frame up is a loop that calls it. They are
  ``add_available_field`` and ``_add_available_calendar_fields``. Two readings:

  - **The tell is not the annotation, it is the last statement.** A predicate
    prefix over a body ending in an assignment or an ``add`` / ``append`` /
    ``update`` call is the whole of the evidence, and it survives a file with no
    annotations at all.
  - **The repair is usually already written down beside it.**
    ``add_available_action(name)`` sat three lines below ``has_field`` spelling
    the same operation correctly, and ``add_used_fields`` below that. §2.4.4's
    "look for the member that already has a spelling" is cheaper here than
    anywhere else, because a mutator's siblings are mutators.
* **This is a different question from the one the previous bullet asks.**
  ``_should_`` is a predicate spelled with the wrong *modality*; these are
  predicates spelled with the wrong *part of speech*. A name can carry both.
* *Frozen reading* (§1.4) at ``a8c1dc581b9``: **499** functions in the core
  package are annotated ``-> bool`` and are neither a ``@property`` nor a dunder;
  **232** wear one of the predicate prefixes and **267** do not. A **candidate**
  population, not a violation count -- most of the 267 are converters, ORM
  acknowledgements, or the reserved ``*_exists`` family, and the first bullet of
  this section is what separates them.

**A sibling family is cheaper evidence than an annotation sweep** ``[review]``,
and it is where the two rules above are easiest to settle. ``odoo/orm``'s
``models/mixins/_cache_scan.py`` is six functions -- ``is_cache_detached``,
``can_scan_identity``, ``can_scan_truthy``, ``can_scan_sorted``,
``can_scan_read`` -- and ``caches_lang_dicts``, a third-person verb among five
canonical prefixes, on the same signature shape and the same return. It is
``has_lang_dict_cache``. *Frozen reading* (§1.4) at ``45117d9469d``: a ``-> bool``
sweep of that package, properties and dunders excluded, returns **33** names
carrying none of the three prefixes, and the first rule of this section is what
separates them -- most are converters and ORM acknowledgements. The family test
returned one name and no false positives. **Where a module is a family of
predicates, the odd spelling is the finding: read the file before sweeping the
annotations.**

**The abolished table maps spellings, not methods** ``[review]``. A row says what
an operation of that family is called; it does **not** say a method wearing that
verb belongs to the family. ``_verifies_tls`` reads down to ``_check_tls`` and is
a predicate: ``_is_tls_verification_required``. **The ratchet's suggested target
is a hypothesis, not a verdict.** Where the body disagrees, the body wins.

**A ``_check_`` that neither raises nor answers is advisory, and is ``_warn_*``**
``[review]``. The rule above says this for an ``@api.constrains`` hook; unbound,
the same body is more common and has nothing pointing at it. ``cli/server.py``
had ``check_root_user`` writing one line to stderr and returning, four lines
above ``check_db_user_not_postgres``, which writes a line and **exits** -- two
contracts under one verb, adjacent, with the caller running both in a row and
able to tell them apart only by reading both bodies. It is
``warn_running_as_root``.

**Read the exit, not only the ``raise``, in a program that has one** ``[review]``.
``sys.exit`` raises ``SystemExit``, so a CLI ``_check_`` that ends in one is in
the Validation row exactly as a ``ValidationError`` would be, and
``parser.error`` -- typed ``NoReturn`` -- is the same. The distinction the row
draws is *does control leave*, not *which statement*: a ``_check_`` that returns
normally on failure is the defect, whatever it wrote on the way.

* **A ``_check_`` that neither raises nor answers nor warns has done something
  else, and is named for that.** ``service/db/lifecycle._check_faketime_mode``
  installed a ``faketime`` ``now()`` function in the database and never raised;
  it is ``_create_faketime_now_function`` (``fd9562fb53e8``). The verb was a
  claim that control might leave, and nothing in the body could make it.

**An adjective-named ``@property`` promises a ``bool``, and returning a count is
the same lie one type over** ``[review]``. Two rules leave this hole between
them: §2.4.4 exempts a ``@property`` from *the verb leads* and allows an
adjective where the value is a ``bool``, and the ``has_unaccent`` rule above
governs only the three prefixes. Neither reaches a bare adjective over an
``int``. ``ConnectionBudget.exhausted`` returned **the number of times the
budget ran out**, beside ``available`` and ``in_use`` -- which are current-state
gauges -- so the name asked a question, the type answered a different one, and
the third sibling was a cumulative counter none of the three names distinguished.
It is ``exhausted_count``.

* **The vocabulary the name declined to use is usually written down beside it.**
  The Prometheus help text for the same value says "**Times** the shared
  connection budget was exhausted", and the test asserting it says "saturation
  must be visible as a **count**". Neither is prose a sweep has to invent --
  **read the metric description, the assertion message and the log line before
  choosing the noun**, because a name that is wrong about its type is usually
  surrounded by text that is right about it.
* **A gauge and a counter in one block of properties is the tell.** Where
  siblings report *what is true now* and one reports *how often something
  happened*, the odd one owes the distinction in its name; ``_count`` is the
  cheapest way to write it and the reason it is not head-first is §2.4.4's
  ``@property`` exception -- the name is the value, not an operation over it.

2.4.9 Execution verbs
~~~~~~~~~~~~~~~~~~~~~

**Do not name a method for the act of running** -- *provisional*. ``_do_``,
``_run_``, ``_perform_``, ``_execute_``, ``_process_`` and ``_handle_`` (census
table) describe execution rather than behaviour; every method executes. Name
the domain operation: ``_post_entries``, not ``_do_posting``. No mechanical
rewrite exists.

* **A callback is a role, not an operation** ``[review]``. ``_callback`` names
  the fact that something calls it back, which every method in a dispatch chain
  does; it is ``_run_server_action``.
* **A protocol member is a batch, not a rename** ``[review]``. ``ir.http``'s
  ``_handle_error`` is this section's verb, and it is mirrored by
  ``HttpExtension`` in ``odoo/http/_protocols.py`` and overridden across the
  addons; the Protocol, the base, every override and the dispatcher that calls
  it move together or not at all (§2.4.14). Left as it is by the ``odoo/http``
  and ``base`` sweeps for that reason, and recorded so the next reader does not
  take it as a one-liner.
* **Where the operation is what the model is about, the verb is a domain verb.**
  ``ir.cron`` exists to run scheduled jobs; ``_eval_`` is what ``safe_eval`` does;
  rendering is a reporting engine's domain operation. The test: could the name be
  replaced by a more specific domain operation? For ``_do_posting`` it could; for
  *run this job* there is nothing more specific to say. Keep one verb and let the
  object separate the scopes -- ``_run_jobs_until_deadline``, ``_run_job``,
  ``_run_job_within_budget`` -- so the grep for the descent is ``_run_``.
* **A count of spellings is not a count of violations, and this rule raises it**
  ``[review]``. Moving a chain onto one verb **adds** a definition to the census,
  and those six verbs are a *sample* -- a verb naming *the walk* is the same
  defect under a word nobody listed (``_traverse_path`` →
  ``_get_update_path_target``). Do not avoid a correct ``_run_`` to keep the
  number still.
* **The tuple return is the tell.** A method returning two products either names
  both or splits, and the **call sites** say which: same consumer → name both
  (``_prepare_body_and_stylesheets``); different consumers → split. **"Unused
  here" is not "unused"** -- grep the workspace, not the file.
* **Where both products share a head, write the head once** ``[review]``.
  ``_available_intervals`` returned the available intervals *and* the occupied
  ones and named the first, which is §2.4.12's "one branch of three" in another
  shape. It is ``_get_intervals_available_and_occupied``: one head, two
  qualifiers, and the count of qualifiers is the count of values -- which makes
  the audit something a reader can do from the name alone.
* **The entry point already names the operation; the descent must wear its noun**
  ``[review]``. §2.4.7's *ask whether the name already belongs to a method one
  frame up* is written there for payload builders, and it is the same test here.
  ``_get_first_available_slot`` dispatched to ``_walk_forward`` and
  ``_walk_backward``, which return a slot and are assigned to a local called
  ``slot``; walking is how, not what. They are ``_get_slot_forward`` and
  ``_get_slot_backward``, which is also what buys ``_get_slot_`` as the grep for
  the descent the ``ir.cron`` bullet above asks for. **The mechanics belong in
  the tail, where they still distinguish the pair.**

* **An execution verb that IS the whole contract survives, and ``NoReturn``
  is what proves it** ``[review]``. The rule objects to a verb standing in for
  behaviour the name declined to state. Where leaving is the behaviour there is
  nothing else to state: ``cli/db.py``'s ``_exit_missing_subcommand`` prints
  usage and exits 2, ``cli/shell.py``'s ``raise_keyboard_interrupt`` is the
  ``SIGINT`` handler. Both would be ``_raise_*`` defects under §2.4.10 -- except
  that its three grounds are *names control flow* (here control flow is the
  operation), *hides control flow* (neither is called directly; each is handed to
  argparse and to ``signal.signal``) and *nothing types it*, which is the one
  that decides. **Annotate it ``NoReturn`` and the name is doing its job; leave
  it ``-> None`` and the name is a lie the type system was willing to catch.**
  ``cli/module.py``'s ``_exit_nothing_done`` claimed ``-> None`` and never
  returned.

* **An abolished execution verb parked in the TAIL is the same defect, and the
  ratchet is blind to it for the same reason** ``[review]``. §2.4.4 says a noun in
  front of the verb hides it from ``classify``, which partitions on the first
  token; a ``_to_<verb>`` or ``_for_<verb>`` tail is the mirror image and hides
  just as well. ``cli/obfuscate.py``'s ``_get_fields_to_process`` and
  ``_get_tables_to_process`` said only that the return would be used, which is
  true of every return. Name the property that selects the members --
  ``_get_fields_selected`` -- or, where the return is a mapping, say that:
  ``_get_columns_by_table``, which also repairs a head that never returned
  tables. **Where one collection feeds two opposite operations** -- both of these
  serve obfuscation and unobfuscation -- **a ``_to_<operation>`` tail is not
  merely vague but false for half the callers**, so writing the operation in is
  not the repair either.
* **``main`` is a binding to the process entry point, not a verb, and a program
  has one** ``[review]``. ``cli/command.py``'s ``main()`` is what ``odoo-bin``
  calls; ``cli/server.py``'s ``main(args)`` booted the server and was reached
  from ``Server.run`` and from ``start.py``, which read ``from .server import
  main``. A reader at that import cannot tell which entry point they hold --
  §2.4.4's unsubstitutable name, manufactured by convention rather than by
  shadowing, and the one shape §2.4.6's shadow carve-out does not cover because
  neither name is the callee's. The repair is the ordinary one, verb and object:
  ``run_server``, which this section already licenses where running **is** the
  operation.

2.4.10 Errors and stand-in names
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**An error is built here and raised there** ``[review]``. A method that builds an
exception is ``_prepare_*_error`` and **returns** it; the ``raise`` is written
where control leaves. ``_raise_*`` is abolished for such a method, on three
grounds in ascending weight:

* it names control flow, which §2.4.9 already objects to;
* it **hides** control flow: ``raise self._prepare_x_error()`` is visible where it
  happens, while ``self._raise_x_error()`` looks like every other call and the
  lines after it are unreachable in a way a reader has to deduce;
* nothing types it. A function that never returns is ``NoReturn``; **0** of this
  repository's **21** ``_raise_*`` model methods say so, and some claim
  ``-> None``, which is false.

The cost is accepted -- the call site says the verb twice, and ``B904`` fires the
moment the raise moves into the caller's own ``except``.

* **The larger half says no verb at all** ``[gate naming_core]``: a builder
  that already returns the exception was invisible to both mechanisms when its
  name is a noun phrase, and is gated now -- ``naming_core_vocabulary``'s
  ``error-builder`` kind (``5b01cd9535ac``) reports a body whose every return
  constructs an exception (a class imported from an ``*.exceptions`` module, a
  subclass of one, or spelled ``*Error`` / ``*Exception`` / ``*Warning`` /
  ``*Denied`` / ``*Exit``), that raises nothing, and whose name is not
  ``_prepare_*_error`` or ``_resolve_*_error``; the ``X_to_Y`` converter idiom
  and a closure filling a same-named parameter slot are exempt. It found
  ``res.config.settings.get_config_warning`` under the Read verb, now
  ``prepare_config_warning``. ``odoo/db``'s ``ConnectionPool._budget_exhausted`` was the shape
  exactly -- it builds a ``PoolError``, its one call site already writes
  ``raise self._budget_exhausted()``, and only the name was missing; it is
  ``_prepare_budget_exhausted_error``. **Being right about the control flow is
  what makes the name the whole of the defect**, and it is why the sweep has to
  read returns rather than grep verbs.
* **A builder of the message is the same family one step down, and takes
  ``_get_*_message``** ``[review]``. ``schema.py``'s ``_not_a_token(kind, value)``
  returned the sentence three DDL guards raise a ``ValueError`` with -- a noun
  phrase, again invisible, and this time not even an exception. Prefer returning
  the exception; where the message is genuinely the shared part and the
  exception class is not, say so in the name: ``_get_invalid_name_message``.
  **A name that describes the failure rather than the value is the tell** -- ask
  what the method *returns*, and let the ``raise`` at the call site keep the
  vocabulary of the failure.
* **A method that raises only sometimes is a different family** ``[review]``. The
  rule above reaches the unconditional raisers (census table); the rest spell
  ``_raise_if_*`` or ``_raise_for_*``, have nothing to return when the condition
  does not hold, and are the Validation row: ``_check_*``.

**A name standing in for another contract takes that contract's spelling**
``[review]``. Four shapes of the same rule:

* a **wrapper** reaching a name the framework resolves at runtime takes the
  callee's spelling and gains only the verb: ``_empty_list_help`` →
  ``_get_empty_list_help``, not the head-first ``_get_help_empty_list``, because
  the two sit four lines apart. **The test is the call, not the resemblance**;
* a **memo** takes the spelling of what it memoizes, since memoizing changes
  *when* a body runs and nothing else: a ``dict``-backed memo over
  ``_resolve_path_def`` is ``_resolve_paths``, not ``_get_paths``. **The memo
  follows the body, never the reverse**;
* a **substitute** keeps the promise the default's name made;
* a **slot** and the method that fills it are one contract under two names. A
  sweep driven by definitions reads ``def``; a slot is a **parameter**. **Read the
  parameter list of every callback-taking constructor in a file you are
  sweeping**.

**``_raise_`` is one spelling of a family, and abolishing it alone moves the
defect rather than fixing it** ``[review]``. ``_reject_``, ``_abort_`` and
``_refuse_`` name the same operation in the same grammar -- a verb for what
control flow does rather than for what the method is about -- and the rule above
reaches none of them; ``_deny_`` is the same shape at **0**. *Frozen reading*
(§1.4) at ``a8c1dc581b9``: the core package holds ``_reject_*`` **5**,
``_refuse_*`` **3**, ``_abort_*`` **1** and ``_raise_*`` **1**; the bundled
addons hold ``_raise_*`` **21**, ``_refuse_*`` **8** and ``_abort_*`` **1**. Read
each against its body and it splits exactly where the two bullets above already
split ``_raise_``:

* raises on a condition, with nothing to return when the condition does not hold
  -- the Validation row, ``_check_*``. ``odoo/http``'s
  ``_reject_wildcard_credentials``, ``_reject_non_json_number`` and
  ``_reject_oversized_body`` are ``_check_cors_credentials``,
  ``_check_json_number_syntax`` and ``_check_body_size``;
* raises unconditionally -- ``_prepare_*_error``, **returning** the exception,
  with the ``raise`` written where control leaves. ``_abort_bad_request`` is
  ``_prepare_bad_request_error``; ``addons/base`` had already settled that
  spelling in ``_prepare_view_error`` and ``_prepare_access_error``.

**The family splits three ways, not two, and the third branch is the one nobody
re-reads for** ``[review]``. Both bullets above assume control leaves. Where it
never leaves at all the method is a **predicate**, and the emphatic verb is what
keeps a reader from checking: ``ir.cron``'s ``_refuse_archived_user(job, env)``
refused nothing -- it logged a warning and returned a ``bool`` its caller spent
as ``CompletionStatus.FAILED if … else None``. It is ``_is_user_archived``.
**Read the body for a ``raise`` before believing any of these four verbs**, and
expect the absence rather than treating it as the surprise: the stronger the verb,
the less likely anyone has looked.

**A verb absent from ``ABOLISHED`` is not thereby permitted.** The table records
the spellings a sweep found, and §2.4.9's own caution -- that its six execution
verbs are a *sample* -- is the same caution here: the family is defined by what
the name talks about, never by the list. ``_assert_`` is the member worth naming
outright, because it reads as *correct* -- the method does assert -- and because
it is test vocabulary migrating into production code, which is a shape a reviewer
can learn to see: ``_assert_dump_sql_safe`` and ``_assert_filestore_dest_free``
both raise, and both are the Validation row.

**A noun phrase that builds an error is this section's, and the paired-model
rule finds it as surely as the body does** ``[review]``. ``fetchmail.server``
carried ``_connection_test_error``, a name with no verb that constructed and
returned the exception ``ir.mail.server`` had already spelled
``_prepare_connection_test_error`` on its own model; §2.4.3's *look for the
same operation on the other half of a paired model* reaches it from the name
alone, and a body read reaches it from the return. Both mail-server models now
spell it the same way (odoo ``52ede28f1c84``).

2.4.11 Partial producers and the ``_find_`` family
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**``_find_`` is three operations wearing one verb** ``[review]``. Pure ORM reads
among them have been renamed to ``_get_``. Split by what the body does, the
``_find_*`` methods that remain (census table) are still not one thing:

* a few perform an ORM read -- and also **write**, which is why they were left
  (``_find_auto_batch`` searches for a mergeable batch, joins the picking to it
  and returns it, and creates one when nothing matches);
* the rest do something else entirely, and the verb flatters them
  (``_find_available_name`` appends ``(2)``, ``(3)`` until unused: a derivation).

The third kind is all but gone. **The canonical is ``_get_or_create_*``**: the
census table counts the methods still spelling it ``_find_`` against those
spelling it ``_get_``. ``_find_`` is not in the abolished table, because
classification needs the body: a pass keyed on the name scored both survivors as
pure reads, and a check for ``create`` / ``write`` / ``unlink`` / ``copy`` moved
them out.

**Read the caller too, because an extension point's body is the least informative
in the tree** ``[review]``. ``_migrate_remote_to_local`` reads as the Predicate
row -- ``return self.type == "binary"`` -- while its caller discards the return
inside ``except (ValidationError, RequestException)``: the contract is *fetch the
remote bytes and store them locally*.

**``_resolve_`` is the verb to keep** ``[review]``, and the census table sets its
size beside ``_find_``'s. It is a **partial** producer, returning
the object or ``None`` meaning *not applicable*; a read that always answers is
``_get_``. Where a dispatch chain mixes the spellings, read it as the chain saying
which branches can refuse.

* **The rule is about the contract, not about fetching.** ``_resolve_runner``
  reads a dispatch table and returns ``None`` for a state with no entry, fetching
  nothing.
* **``_resolve_`` is not every optional return.** ``_get_stored_content`` returns
  ``None`` when there are no stored bytes -- there ``None`` is *there is none*.
  **The test is the caller, not the annotation**: ``_resolve_`` earns its verb
  where the ``None`` routes somewhere.
* **Check a reserved verb against the body twice**: once for the contract, once
  for the possibility that it was never a claim about the contract at all.
  ``_resolve_filestore_root`` took its verb from ``Path.resolve()`` and always
  answers; it is ``_get_filestore_root_path``. **The borrowed verb is as often
  the receiver's own**: ``ir.asset.paths``' ``_resolve_targets`` took it from the
  ``self.resolve(target)`` on its second line, warns and returns ``[]`` where
  that finds nothing, and is ``_get_target_paths``. A verb one line below the
  ``def`` is the likeliest source and the hardest to see.
* **And ``_get_`` is not always where it lands** ``[review]``. The section's
  counterexamples are reads; the other wrong sense is the **constructor**.
  ``ir.mail.server``'s ``_resolve_smtp_transport`` assembled an ``_SmtpTransport``
  out of the record's fields or its keyword arguments, always answered, and
  handed the result to ``_open_smtp_connection`` -- §2.4.7's *object construction
  takes* ``_prepare_``, *a factory having a consumer like anything else*. It is
  ``_prepare_smtp_transport``. **Ask what the body does with the value before
  reaching for the read verb**: assembling one is a payload operation and
  ``_get_`` would be a second wrong answer, not a repair.

**A private method paired with a public one of the same spelling cannot be renamed
alone** ``[review]``. A pair split across two spellings is worse than a pair
uniformly wrong. **Rename the pair or neither**, and where the public half needs
an ADR, the private half waits for it.

**A context manager is named for the scope it opens** ``[review]``. The teardown
after the ``yield`` is half the contract, so a name promising a return states the
half that is least true. Name the scope in the imperative --
``_staged_filestore_temp`` → ``_stage_temp_file``, on the model of
``borrow_request``, ``savepoint``, ``ignore_indexes``.

**And it can never be a field hook**, so §2.4.1's reserved-prefix test applies to
a ``@contextmanager`` unconditionally -- there is no declaration that could make
the prefix honest. ``hr.employee``'s ``_domain_errors_as_access_errors`` wore
``_domain_`` while opening a scope in which a domain's ``ValueError`` surfaces as
an ``AccessError``; it is ``_mask_domain_errors_as_access_errors``. **Read the
decorator before the name**: the two gates keyed on field declarations cannot see
a hook prefix here at all, because nothing points at the method.

**And it may be named for the noun it yields, which slips past the no-verb rule**
``[review]``. The rule above reaches a name that *promises a return*; the commoner
shape simply **is** the value. ``cli/command.py``'s ``odoo_env`` built a
``Registry``, opened a cursor and yielded an ``Environment``, stating neither the
scope nor the teardown that is half its contract -- and it reads as finished
because a ``with`` statement reads as a declaration rather than a call, which is
why §2.4.4's *a name with no verb at all* fires for nobody here. A
``@contextlib.contextmanager`` is a ``def`` like any other: it is
``open_environment``. The ``odoo_`` prefix, which says nothing inside ``odoo/``,
went with it.

**Get-or-create hides under a bare create verb, not only under ``_find_``**
``[review]``. The canonical above repairs ``_find_auto_batch``, whose caller uses
the return; the same body wearing ``_create_*`` is harder to see, because the verb
is not wrong
so much as half. ``cli/scaffold.py``'s ``_create_directory`` resolved the path,
created it only when absent, exited when it was not a directory, and returned it.
**The tell is that the caller uses the return**: a ``_create_`` whose return is
discarded is a create; one whose return is consumed, over a body carrying an
existence check, is ``_get_or_create_directory``.

**The canonical repairs the family and not every member of it** ``[review]``, and
this section named its own counter-example for months. ``_find_existing_rule_or_create``
wore the shape exactly -- search, then create -- and was cited here as what
``_get_or_create_*`` repairs. It is not a get-or-create at all. It returns
**nothing**, both call sites invoke it as a bare statement, and what it does is
write the rules whose stored values differ from the supplied ones, create the ones
missing and leave the rest alone: convergence on a source of truth elsewhere, which
is §2.4.12's reserved ``_sync_``. **The tell one paragraph up is what settles it**,
turned on the paragraph's own example. Two independent checks agree -- the module
was already spelling the operation ``_sync_resupply_routes`` in the same file, and
``_get_or_create_rules`` is refused by ``naming_core_vocabulary``'s ``empty-return``
rule, because a ``_get_`` prefix promises a return this body does not have. So the
prescribed canonical was a name no gate would have accepted. It is ``_sync_rules``.
**Read the body against the tell before taking a canonical, including when the
section hands you the example.**

2.4.12 Mutation, sync and overloaded verbs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**``_update_``, not ``_set_``** ``[review]``, for a method that writes to records
and is wired to nothing. ``_set_*`` is a large family beside ``_update_*`` (census
table), so this is a backlog rather than a tidy-up. Three carve-outs, all
bindings:

* an ``inverse=`` target is ``_inverse_<field>`` and was never a ``_set_``
  question -- the ``_set_`` spelling is all but drained (census table);
* ``set_values`` / ``get_values`` on ``res.config.settings`` are *bound by name,
  not by inheritance* (§2.4.14);
* ``set_param`` on ``ir.config_parameter`` is public and reached from JS and XML
  data.

Where ``_set_x`` and ``_update_x`` both exist for one operation, that collision is
the duplicate report this section exists to produce.

**A method that converges is not a method that writes**
``[gate doc_restated_counts]``. Making one table **agree with** another takes a
create where the target is missing, a write where it differs and an unlink where
the source is gone. **The canonical is ``_sync_*``**, and the tree had a family
for it this section had never named: the census table counts the definitions
spelling it ``_sync_*`` and ``_synchronize_*`` beside ``_update_*``'s. It is not
merged into ``_update_`` -- the verb carries a fact the other does not, that there
is a source of truth elsewhere. ``[review]`` rather than ``ABOLISHED``, since not
every ``_synchronize_`` is this operation.

**A name that announces one branch of three is wrong in the same way as a hook
named for one of its fields** ``[review]``. ``_reserve_paths`` reserved a path,
moved one whose path had changed, and **deleted** a reservation whose path was
cleared; it is ``_sync_path_reservations``. **Where a test and the method it
covers disagree about what the operation is, prefer the test's word.**

**``_post_`` is overloaded** ``[review]``. Its definitions (census table) carry
three unrelated meanings -- ``account.move._post`` (accounting), ``message_post``
(mail) and HTTP handlers. Do not add a fourth: new code names the domain
operation. The existing three are load-bearing.

**And a fourth reading is not a fourth meaning: it is a different word**
``[review]``. In ``_post_write``, ``_post_load_data``, ``_post_process_picking``,
``post`` is the prefix *after* -- an adverb bound to the operation behind it, not
the verb any of the three above uses. *Frozen reading* (§1.4) at ``75ef0eec641``,
hand-classified: of **139** ``post_*`` model methods, **52** read this way, which
makes it the largest reading after the three the rule names. Two consequences.
The census counts spellings and cannot separate them, so **do not read 137 as
three families**. And "new code names the domain operation" does not reach these:
an after-``write`` hook has no domain operation to name, because it is named for
*when* it runs. Keep the prefix, and keep an ORM operation immediately behind it
so the adverb reading is forced -- ``_post_write_workcenter`` survives, while a
``_post_workcenter`` would collapse into the verb.

**A ``_toggle_`` handed the new value is an ``_update_``** ``[review]``, and the
signature is the whole test -- it does not need the body opened. The verb claims
the method read the current value to pick the new one; a parameter carrying the
new value says it did not. *Frozen reading* (§1.4) at ``75ef0eec641`` over
§2.4.3's population: **24** ``toggle`` model methods, of which **13** take the
value they claim to toggle (``toggle_is_reached(is_reached)``,
``_toggle_template_mode(is_template)``, ``_toggle_view(xml_id, active)``), **9**
decide for themselves and are correct (``toggle_lock``,
``toggle_message_starred``, ``toggle_debug``), and **2** take *which record*
rather than *which value* (``ir.cron.toggle``, ``toggle_noupdate``) and are
correct too.

* **The signature is a lower bound on the family, not the whole of it.** The new
  value can arrive through the **name** instead:
  ``account.account._toggle_reconcile_to_true`` and ``._toggle_reconcile_to_false``
  take no argument, pass the signature test, and neither toggles anything. The
  rule is *the new value arriving by any route*; the signature is the half that
  can be checked without reading.

**The Mutation row's discriminator is the write, not the ORM** ``[review]``. A
method handed a ``dict`` its caller owns, which adds to it, is this row and not a
payload builder, even though no record is written; §2.4.7's parameter-list test
is what separates the two.

**A producer prefix on a body that hands nothing back is this row** ``[gate
naming]``. ``_get_``, ``_resolve_``, ``_prepare_`` and ``_generate_`` each claim
a return -- the Read row's value, §2.4.11's object-or-``None``, the Payload
row's mapping, §2.4.7's manufactured artefact. A body
under one of them that never ``return``\ s or ``yield``\ s a value, and instead
stores into something or writes records, did this row's work under a producer's
name: filled a dict the caller owns (``_prepare_request(url, kwargs)`` setting
``kwargs["timeout"]``, ``_resolve_fallback_accepted_values(fallback_values)``
adding a key "in place"), wrote fields on the receiver
(``account.online.link._get_access_token`` assigning ``link.access_token``),
re-pointed a record it searched for (``_get_or_create_payment_channel``, whose
callers never read the return). All are ``_update_`` -- or, where the body is a
whole operation the prefix hid, that operation's verb: ``_send_refusal_mails``,
``_create_missing_uom_hours``, ``_sync_payment_channel``. The rule reads the
body because the name cannot be trusted here by construction: the prefix is the
claim under test. *Frozen reading* (§1.4) of the rule over odoo
``366986f0dcd3`` and enterprise ``1a10fe02ba4``, the commits that renamed ahead
of it: **4** in ``addons/``, every one in a file another session's sweep was
already carrying; **0** in ``agromarin``; **31** in ``enterprise`` (23 of them
``_prepare_``, eleven in one ``l10n_in_reports`` spreadsheet writer whose
``_prepare_<section>_sheet(workbook)`` fills a sheet), banked into that floor
with a note saying the scan grew and not the tree.

* **The store-or-write test is what keeps this from reading as "no return means
  mutation".** A body with no product and no store is some other question:
  ``_get_reconciled_checks_error`` only raises and is §2.4.8's; a
  ``_get_..._vals`` whose base branch raises ``NotImplementedError`` and whose
  override returns is an extension point. Three more are left alone on the same
  argument. An extension stub -- docstring, ``pass``, a bare ``return``,
  ``check_singleton()``, a ``raise`` -- returns nothing because it does nothing
  yet, and its overrides carry the contract. A body whose last statement raises
  is §2.4.10's question. And a name a field declaration in the same file binds
  as a hook belongs to ``field_hook_naming.py``, whose ``unprefixed`` kind names
  it (``_get_mo_count`` assigning five ``count_mo_*`` fields is a
  ``_compute_``); reporting it here too would be one question answered by two
  gates.
* **It found missing returns as well as wrong names, which is the case for
  reading the body.** ``_get_or_create_uom_hours`` and
  ``_get_or_create_payment_channel`` both created the record and dropped it;
  their callers -- an XML ``<function>`` and two ``write`` hooks -- had already
  stopped reading a return that was never there. A name can promise more than
  the body delivers, and only the body says so.
* **``naming_core_vocabulary.py`` asks the same question of its eight scopes
  as ``empty-return``**, keyed on ``get`` and ``prepare`` and without the store
  test, and holds each at a hard zero with an argued allowlist. The two do not
  double-report today because those scopes read zero under both; where they
  ever disagree, the shared gate's store-or-write test is the narrower reading
  and the one to trust.
* **``_generate_`` joined the producer verbs, and the printed canonical splits
  on the write.** ``res.users._generate_missing_avatars`` wrote ``image_1920``
  on the receiver and returned nothing -- the Mutation row's work under
  §2.4.7's largest payload verb -- and is ``_update_missing_avatars``. The rule
  reads the writes rather than printing ``_update_`` unconditionally: a body
  whose **only** ORM write is ``create()`` and that stores nothing took the
  domain operation's name (§2.4.7's ``_generate_consume_moves`` →
  ``_create_consume_moves``), and prints ``_create_``; a ``write()`` or
  ``unlink()`` beside it makes the body a mutation again. *Frozen reading*
  (§1.4) at the commit that landed it: **18** in ``addons/`` (15 ``_update_``,
  3 ``_create_``), **44** in ``enterprise``, **3** in ``agromarin``. Two
  cautions from reading those lists. A public ``generate_<x>_report`` on a
  wizard that writes the file to a field and returns nothing is *reported*
  correctly and *targeted* wrongly -- it is a button, and §2.4.16 owns it. And
  the eleven Swiss payroll declarations that read this way are one shape in
  one module, which is a family finding and not eleven.

2.4.13 Scope, adoption and the ratchet
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**The vocabulary governs model methods** -- classes deriving from
``models.Model`` / ``TransientModel`` / ``AbstractModel`` -- **and every function
in the core package ``odoo/``**, at module level and on plain classes alike. A
helper in an addon's ``models/`` may not borrow another vocabulary either,
whether or not it is indented under a class.

**The package carve-out that stood here is retired** ``[review]``. It exempted the
framework packages below the ORM (``odoo/db``, ``odoo/http``, ``odoo/tools``,
``odoo/orm`` internals) on the ground that they legitimately speak SQL and Python
data-structure vocabulary. Read against the bodies rather than the package names,
that was true of a handful of names and false of the rest: what the sweep found in
core was ordinary misnaming -- a ``_validate_`` that raises, a ``_fetch_`` that
reads, an ``_ensure_`` that returns a value it built, a ``_fill_`` that writes --
and four spellings that were never claims about a verb at all. **What survives the
vocabulary in core is a list, not a package boundary**:

* **``fetch``** is the ORM read operation and now has a row in the reserved table
  above.
* **``append_paths``** keeps its verb because both halves of the ``_append_``
  reservation hold: the receiver is an ordered list and the addition lands at its
  end, beside an ``insert_paths`` that takes the index.
* **Three infix hits are nouns wearing a verb's spelling**, which is the case
  §2.4.4 warns the ratchet cannot tell apart: ``fill_temporal`` is a ``read_group``
  parameter and a context key, ``on_delete`` is a field on ``ir.model.fields``,
  and a control character is a character. A fourth, ``ensure_db``, was argued
  as a named concept -- ``ENSURE_DB_PATHS``, ``register_ensure_db_paths``,
  ``is_ensure_db_path`` and the ``web`` controller function they are named for
  -- and held out of the rename on the ground that renaming one half would
  split the pair. The pair is renamed together instead (2026-09-09): the
  function selects the request's database from its parameter, the session or
  the single database on the cluster and redirects when none can be settled,
  so it is ``select_db``, and the registry is ``SELECT_DB_PATHS`` with
  ``register_select_db_paths`` and ``is_select_db_path``. Only the
  ``test_http`` route URL keeps the old word, being a URL.

**A bool return moved a name across the table, not just along it** ``[review]``.
``validate_csrf`` answers a question and never raises, so the Validation row sends
it to the Predicate row rather than to ``_check_``; ``verify_hash_signed`` returns
the message or ``None`` and lands on ``_resolve_`` (§2.4.11); ``validate_url``
prepends a scheme and returns a URL, so it was a converter mislabelled as a check.
**Read the return before reading the verb.**

**It governs the module's own helpers too, and the gate now sees them**
``[ratchet naming]``. ``naming_vocabulary.py`` implemented the scope as a
*class-membership* test, so two populations in the same files were counted by
nothing: a function declared at **module level** under ``models/`` and
``wizard/``, and a method on a **plain class** declared in the same file; the
census table counts both, and the classes. Both are in ``measure()``'s population
now, over the addon trees only -- a directory test alone would sweep in ORM
internals the vocabulary does not reach, so the discriminator is a
``__manifest__.py`` above the file, which is what makes a directory an addon and
what the core package has none of.

**And the directory list that widening introduced stops at two, so no gate has
ever read an addon controller** ``[review]``. ``ADDON_HELPER_DIRS`` is
``{models, wizard, wizards}``. A controller class derives from
``http.Controller``, so ``is_model_class`` is false for it, and its directory is
not in that set, so ``governs_module_helpers`` is false too: every route handler
and every module-level helper under an addon's ``controllers/`` fails *both*
tests and is in the population of nothing. It is not a thin scope, it is an
absent one -- and ``addons/web``, which is twenty-four controller files against
twenty-six model files, was reported clean by a gate that had read fewer than
half of its definitions.

*Frozen reading* (§1.4) at ``f5d34bc3c95`` / ``749c3caa2b4`` / ``34a3b5c5e2d`` /
``cc15c000fb0``, measured in detached worktrees at those four commits by adding
``controllers`` to that set and diffing the violation **sets**, not the counts.
The worktrees are the measurement, not a formality: the same script over the
shared checkout read **63** for ``odoo`` on the same afternoon, because four
sessions were mid-rename in it, and a figure taken from a tree nobody can name
is not a reading of the branch.

=================  ========  =======  =====
Scope              Before    After    New
=================  ========  =======  =====
``odoo``                  0       61     61
``enterprise``          213      236     23
``agromarin``             0       26     26
``design-themes``         0        0      0
=================  ========  =======  =====

**Read that table as newly VISIBLE names, not as new offenders.** Every one of
the 110 predates the measurement and none arrived with it; what moved is the
scan, under a fixed tree. That is the middle row of §4's three failure modes --
the one neither re-measurement nor ``ratchet.py --list`` can detect, because
after a scan widens every reading agrees with itself and with every later
reading -- so the distinction survives only if the note carries it. State it in
those words when banking any floor this reaches, the way ``naming_enterprise``'s
note does.

**AND ``controllers`` IS ITSELF ONE SLICE OF THE HOLE.** Three sessions asked the
same question and each measured the directories it thought to name, so each
answered a different subset: controllers alone is the table above, and
controllers plus ``tools`` is 146. Measured over **every** directory of an addon
instead -- ``classify`` and ``_overrides_same_name`` applied exactly as
``measure()`` does, on top of what is already governed -- the hole is **243**.
*Frozen reading* (§1.4) at ``e6e7d07e169b`` / ``d09bfed781b`` / ``125a5ceec`` /
``cc15c000f``:

=================  ======  ===========  =====  ==========  =====
Scope              Hidden  controllers  tools  migrations  other
=================  ======  ===========  =====  ==========  =====
``odoo``              116           60     29           0     27
``enterprise``         52           23      0           0     29
``agromarin``          75           26      7          23     19
``design-themes``       0            0      0           0      0
=================  ======  ===========  =====  ==========  =====

**The ``other`` column is the finding, and it is 75 definitions nobody enumerated**
-- reached by neither earlier measurement, because both scans named the
directories they were looking for and a directory nobody names is a directory
nobody counts. That is §2.4.13's own blind spot recurring inside the attempt to
measure it: the fix for *a scan that stops at a list* is not a longer list.

**243 is the size of the hole and NOT the size of a backlog**, and one bucket is
why. ``agromarin``'s 23 ``migrations`` hits are one-shot upgrade scripts, and
whether §2.4's vocabulary governs a migration script **at all** is a different
question from whether it governs a controller -- one a widening would answer by
accident. Settle it before counting those 23 as debt.

**And it is already answered inconsistently, by mechanism rather than by
anyone's decision** ``[review]``. The two gates disagree about migrations and
neither disagreement was chosen. *Frozen reading* (§1.4) at ``04e2c12365d2``:
``naming_vocabulary``'s file walk reaches **318** migration files under
``addons/`` and governs **0** of the **500** functions in them, because its population is model classes and a migration script declares
none; ``naming_core_vocabulary`` scans ``rglob("*.py")`` and reads every function,
so at a governed scope it reads them all -- and has already renamed one
(``_seed_missing_steps``). So the same script is ungoverned by one gate and
gated by the other, and a reader who asks "does the vocabulary govern
migrations" gets a different answer depending on which gate they ask. **A rule
that two gates answer differently has not been decided, it has been
implemented twice**; that is the thing to settle, and the 23 are only its
visible edge.

**The widening is not landed, and the reason is the floors rather than the
names.** ``odoo`` and ``agromarin`` are at zero, and §9.4 calls a sibling zero a
contract rather than debt, so a one-word change to a shared constant would put
110 offenders through three floors that are all currently hard zeros -- and the
repair is thirty-odd modules nobody has read. The population is real and it is
lopsided: of ``odoo``'s 61, **41** are the Validation row -- ``verify`` 23,
``validate`` 15, ``ensure`` 3 -- and **19** of those 41 sit under
``addons/payment*``, one ``_verify_signature`` per acquirer, each checking a
webhook's HMAC. The remaining twenty are the Read row (``fetch`` 12), the
Payload row (``build`` 4, ``make`` 3) and one ``delete``. **A single row
carrying two thirds of an unread population is the argument for reading it**:
these are not scattered stylistic misses, they are one operation spelled three
ways across twenty modules that copied each other. Whoever takes it should take
one repository at a time.

**And fix ``SKIP_DIRS`` before widening anything, because it spells the wrong
word.** ``naming_vocabulary.SKIP_DIRS`` carries ``vendored``; the two directories
in this workspace are ``odoo/odoo/libs/_vendor`` and
``addons/auth_passkey/_vendor``, and neither matches. The core one is harmless --
``naming_core_vocabulary.py`` opens with ``SKIP_DIRS = nv.SKIP_DIRS |
{"_vendor"}`` precisely because that gate reads the core package -- so the
exposure is the sibling gate's alone, and it is 11 definitions:
``verify_registration_response``, ``verify_authentication_response``,
``validate_certificate_chain`` and eight more attestation verifiers under
``_vendor/webauthn``. **A widened population would bank all eleven as ours**, and
they are a vendored library implementing the WebAuthn spec's own vocabulary --
§2.4.13's opening rule is that the vocabulary governs *this* repository's methods,
and vendored code is not ours to rename.

**It looks like one word in a frozenset and it is not, which is the more useful
half of this paragraph.** An earlier draft said exactly that; the change was made,
predicted to be a no-op, measured, and was not. Read the block as a **delta over
one tree** and not as four absolutes -- it was taken in a shared checkout, which
the ``methods`` control row is there to make safe: it does not move, so what the
other rows show is the frozenset and nothing else.

.. code-block:: text

   bool_returning_predicates   276 -> 274
   bool_returning_others       355 -> 348
   methods (control)         26,248 -> 26,248
   naming_vocabulary --count        0 -> 0

Nine vendored definitions feed two **published census rows** -- ``is_rsa_pkcs``
and ``is_rsa_pss``, plus seven ``verify_*``/``validate_*`` attestation checks.
``measure()`` is model-class-scoped and returns none of them, but ``census()``
calls ``_bool_annotated``, which reads **top-level functions in every scanned
file** with no model-class test at all; the two disagree about their own
population, and checking the gate tells you nothing about the block. **The gate
reads 0 on both sides**, so no amount of re-running it can reveal the move.

**And the two populations are different sets, so neither number predicts the
other**: 11 names would be flagged by ``classify()`` under a widened population,
9 feed the bool rows, and the overlap is **7**. The two ``is_rsa_*`` are
correctly-named predicates that leave the scan anyway, and four offenders --
``verify_registration_response``, ``verify_authentication_response``,
``verify_signature``, ``verify_safetynet_timestamp`` -- are not bool-annotated
and move no row. Reasoning from "11 offenders" to the census cost, or back, gets
both wrong.

That is §4's middle failure mode -- the scan narrowing under a fixed tree -- with
the sign that reads as *progress*: two rows fall by nine and the tree has not
improved by one name. So the fix must land with a banking note saying **nine
vendored definitions left the scan, not nine renamed**, and it must not land
while anyone is renaming inside ``bool_returning_*``. The core gate's
``nv.SKIP_DIRS | {"_vendor"}`` is genuinely free only because
``naming_core_vocabulary.py`` has no census.

**What was done first is the per-scope gate**, which reaches the same files
without moving a shared floor: ``naming_core_vocabulary.py`` reads *every*
function under the scope it is pointed at, so adding ``web`` to its
``GOVERNED_ADDONS`` put those twenty-four controller files under a hard zero of
their own, argued by allowlist rather than banked. That is still the repair for
the **body-reading** rules, which travel only to a scope somebody has read.

**The widening itself landed on 2026-09-09** ``[ratchet naming]``, and it is
not a longer list: ``governs_module_helpers`` is now *a file under a
``__manifest__.py``*, full stop -- ``controllers/``, ``tools/``, ``report/``,
``utils/``, a module's top-level ``utils.py`` and ``hooks.py``, and
``migrations/``, which is the question the two gates had answered differently
by mechanism and now answer the same way: an upgrade script's helper is this
repository's code, reviewed like any other, with no binding a rename could
miss. ``SKIP_DIRS`` spells ``_vendor`` in the same change, so the eleven
WebAuthn verifiers left the scan as the block above predicted. §2.4.20's
synonyms joined the table in the same commit, so the readings below carry both
moves at once. *Frozen reading* (§1.4) at ``3e297bb9ff4b`` / ``7634473eeab`` /
``301e2ca79`` / ``cc15c000f``, in a detached worktree carrying only the gate
files:

=================  ========  =======  ==============
Scope              Before    After    Floor banked
=================  ========  =======  ==============
``odoo``                 19      159   159, exact
``enterprise``          195      275   275, no-increase
``agromarin``             1      116   116, no-increase
``design-themes``         0        0   --
=================  ========  =======  ==============

**Every one of the 140, 80 and 115 is newly visible and none is new**, and
the banking notes say so in those words. The 19 ``odoo`` was already red
against a floor of 0 before this change -- eighteen ``account`` report names
that arrived with the 2026-09-09 sync -- so the table's *Before* column is a
reading of the tree, not of the floor. **The odoo floor is banked at 159 so
the sweep can proceed in batches under an ``exact`` floor**, each batch
re-banking downward in its own commit; the two sibling floors are banked at
their readings so that §9.4's contract is stated as a number rather than as a
red gate nobody owns, and the ``agromarin`` 116 is owed: 27 of them are the
``migrations`` bucket this section priced at 23 before the synonyms, the rest
are one ``marin`` model's ``_calculate_*`` family, the ``telegram_bot_*``
controllers and the ``_detect_`` predicates.

**A function nested inside a method is the third such population, and the
largest** ``[gate doc_restated_counts]``. The scan read ``tree.body`` for module
level and a class body for its methods, so a ``def`` written inside a method body
was reached by neither test: they sit on model methods in this repository in
greater numbers than either population above (census table). It is in the gate's
population now, at every depth and counted once however deeply nested -- reaching
a closure inside a closure means walking from every function rather than from the
module, which visits the inner one once per enclosing frame. They are also the
cheapest names
in the tree to repair, because a nested function is reachable from nothing
outside the body that declares it -- no binding (§2.4.14), no override, no call
site a grep can miss, and no other owner to collide with. **A sweep that leaves
them out is leaving out the half of its own work that costs nothing.** ``mrp``
alone held six with no verb at all: ``fallback_loc``, ``next_move``,
``workorder_order``, ``operation_key_values``, and ``_keys_in_groupby`` twice.

* **The leading underscore means nothing here, and is better dropped.** It marks
  a member private to a class; a nested function is private to a *body*, which no
  caller can reach at all, so the underscore says only that its author was
  matching the methods around it.
* **A nested function passed as an argument is a slot** (§2.4.10), and the slot
  is a parameter of the callee, not a ``def`` a definition-driven sweep will
  read: ``_keys_in_groupby`` was handed to ``stock``'s ``groupby_method=`` and is
  ``get_groupby_key``.
* **It is invisible to the reviewer as well as to the gate**, which the other two
  populations are not: a nested ``def`` appears in no outline and in no search
  for ``^    def``. **Grep ``\bdef `` when sweeping a file**, and expect a higher
  count than the class body suggests.
* **A closure is where a vocabulary drifts**, for the same reason it is cheap to
  fix: nothing outside the method can collide with the name, so nothing pushes
  back on a private spelling. The freedom and the drift are one fact.
* **The backlog inside it is drained, and that was always the point**
  ``[gate doc_restated_counts]``: of them, **0** open with a verb the abolished
  table reports and **7** with a reserved one. It was 8 and 7 when this
  bullet was written, which is what made the population worth naming as a
  discipline rather than as debt -- and the gate that could see it did not exist
  yet, so the eight were swept by hand. Four more became visible when
  §2.4.20's synonyms joined the table (below) and were swept with the
  ``naming`` floor the same day; the population is gated now, not a backlog. ``naming_vocabulary.py`` measures this
  population now, so the zero is held rather than observed: the cost of leaving
  it ungoverned was never a pile of bad names, it was that nothing stopped one
  forming.

**A third population is nested inside the first two: the closure** ``[review]``.
``naming_core_vocabulary.py`` reads every ``FunctionDef`` in the core package, so
it does see a nested one -- but the ``[review]`` rules of §2.4.4 and §2.4.9 are
the ones that bite here, and a closure is where they are least likely to be
applied, because the name is visible in one screen and the author is not naming
anything for a stranger. It is exactly the place a bare execution verb survives:
``odoo/db/metrics.py``'s ``log_sql_stats`` defined ``def process(log_type)``, a
``_process_`` in a package whose vocabulary abolished the verb everywhere else,
and it is ``log_direction_stats`` -- and the enclosing function was
``print_log`` until ``d29958b31396``, a body that logs at ``DEBUG`` through a
logger and never prints, so the verb on the outer name was a lie the inner
one inherited. Two readings:

* **A closure passed as an argument is a slot** (§2.4.10) and takes the callee's
  contract: the ``re.sub`` replacement in ``ddl.py`` was ``_sub_named`` -- named
  for the API it is handed to -- and is ``_replace_named_marker``; the ``query=``
  callback in ``bulk.py`` was the participle ``rendered`` and is
  ``render_copy_statement``.
  **Named for the callee's *parameter* is the same defect one step worse**:
  ``_sub_named`` at least said which API it served, while ``http/openapi.py``'s
  ``repl`` is what ``re.sub`` calls that argument in every use of ``re.sub``
  anywhere, so it distinguishes nothing and cannot say which substitution it is.
  It turns a werkzeug rule argument into an OpenAPI path placeholder and collects
  the parameter's schema on the way: ``replace_rule_arg_with_placeholder``. **A
  parameter name is the least informative name available**, because the callee
  chose it once for all of its callers.
* **Being local is an argument for the rule, not against it.** A closure is read
  in the same breath as its call site, so a name that only makes sense there is
  the cheapest kind to get wrong and the cheapest kind to fix -- nothing outside
  the function can hold it.

**A module-level alias is a definition with no ``def``** ``[review]``, and it is
the cheapest way to put one operation under two names. ``a = b`` at module scope
binds a second public name that every mechanism in this section misses, because
``census()`` and ``naming_vocabulary.py`` both walk ``FunctionDef``.
``odoo/http/request_class.py`` carried ``clear_monodb_cache =
clear_db_list_cache``: one function, two spellings, two vocabularies -- §2.4.17
decides for ``invalidate_``, which is what the body already said -- and nine call
sites split across the two names. *Frozen reading* (§1.4) at ``a8c1dc581b9``: the
core package holds exactly **two** aliases of a function defined in the same
file, that one and ``tools/translate.py``'s ``_ = get_text_alias``, which is the
gettext idiom and correct. A population of two is not a backlog; it is the
cheapest moment to write the rule down.

**The alias is invisible in both directions, and the second one is what bites.**
The census cannot see the name, and a person auditing the rename greps the
alias's *target* -- which finds the definition and not one of the alias's callers.
**Grep the alias's own name before deleting it.** Removing this one on the
target's evidence alone took ``test_http`` to 28 errors of 39.

**A file can be sixteen names wrong and green** -- three sweeps left the ratchet
reporting the same count before and after, which is the argument for the
``[review]`` tier. Read the body of every name in an ungated file.

**Two gates, and both readings of 0 mislead, differently** ``[review]``.
``naming_vocabulary.py --roots odoo/odoo/orm`` read **0**, and that reading was
close to meaningless: its population was model-class methods while that package is
overwhelmingly plain classes and module-level functions, so ``--roots`` made a
scope look measured that was never in the population. That half is closed for the
addon trees and deliberately left standing for core, which the sibling gate owns.

**And a gate reading 0 is not evidence, which took two independent widenings to
say with a number** ``[review]``. ``--roots addons/account`` read **0** while ten
names in that module were wrong. Four of them needed the Payload row's assemble
verbs to be flagged whatever their tail (§2.4.7), and **sixteen** across
``addons/`` needed *both* that and the scope above -- an assemble verb with no
payload suffix, declared inside a method. Each change alone reports zero of the
sixteen. **Two tightenings agreeing on 0 is not two confirmations**; it is one
population neither of them contained.
``naming_core_vocabulary.py`` holds the right population for core and also reads
0. **The wrong gate reading 0 is the trap the flag sets** -- it answers the
question asked without making the population the one wanted. The sharper case is
the opposite one: over ``odoo/odoo/addons/base`` the sibling gate's 0 is entirely
**sound**, that tree being model classes, and it was still worthless, because
every finding there was ``[review]`` tier. **The right gate reading 0 is the more
dangerous of the two, because nothing about it looks wrong.**

**Adoption** ``[review]``. As with §2.2, apply the vocabulary to methods
you create or substantially rework. ``naming_vocabulary.py`` counted definitions
still using an abolished verb in all four repositories and every scope had
reached **zero** when the gate was removed with ``tooling/`` on 2026-09-11; the
census figures in this section are as of that day. A new abolished verb is a
review finding now.

It measures the **mechanically decidable** rules only -- the abolished-verb list.
The ``_get_``/``_prepare_`` split and the two *provisional* rules are excluded by
design, because a floor nobody can lower by reading the rule is a floor people
learn to ignore.

2.4.14 Bindings a rename must carry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**A rename carries its bindings, and that is the whole of the constraint**
``[review]``. *Inherited* is not a property of a name but a statement about who
else holds it, and ``git grep -ln '<name>' 19.0`` answers it against the pristine
mirror. That buys an estimate of the work, not a veto.

* **Greppable, inside the workspace** -- an XML ``name="..."``, a JS reference, an
  override in a sibling checkout. **Cost, not a veto**: rewrite them in the same
  commit. A Python-only refactor breaks them silently and no gate catches it.
* **An ``__all__`` entry is a position, not only a spelling** ``[ruff RUF022]``.
  Re-sorting it is part of the rename, not a follow-up, and the toolchain splits
  in a way that hides it: ``ruff format`` leaves ``__all__`` in whatever order it
  finds, so a rename that moves a name's alphabetical position is invisible to
  the formatter and surfaces only in ``ruff check``, which runs at a
  **hard zero** over ``odoo/``. Verified by probe rather than by reading, since
  ``explicit-preview-rules`` makes the family selector an unreliable guide: an
  unsorted ``__all__`` under this repo's own config reports ``RUF022`` and
  survives ``ruff format`` untouched.
* **Computed from data** -- a migration, not a rename.
* **Reachable from outside the workspace** -- a public method an integration may
  call over RPC. Weigh it as a public-surface change, and consider leaving the
  old name as a delegating shim. **A CLI subcommand is this category too, and the least
  visible member of it**: ``odoo-bin db drop`` is written down in shell history,
  runbooks, cron entries and other people's scripts, none of which this
  workspace can rewrite and none of which any grep here can see, because the
  caller is a person. §2.4.6 is where that lands as a naming rule.

**A rename has two mechanical failure modes and they are the same failure**
``[review]``. This section says which bindings a rename must carry; it says
nothing about the substitution that carries them, and that is where a sweep
actually goes wrong. Both modes come of a tool that reads a *name* and cannot
tell a **definition** from a **use**:

* **Under-reading.** A binding grep whose output was capped -- a ``head``, a
  pager, an editor's match limit -- reports a subset and looks complete, because
  a rename that has found some call sites looks exactly like one that has found
  all of them. Two sessions hit this on one day; one lost seven call sites in a
  localisation test suite to a ``head -10`` that ``addons/base`` alone filled.
* **Over-writing.** A substitution on a bare name rewrites every *use* of that
  spelling, and a local variable, a parameter, a keyword argument, a dict key or
  a selection value is a use. ``sql.table_kind(...)`` assigned to a local called
  ``table_kind`` produced ``get_table_kind = sql.get_table_kind(...)`` in two
  repositories; a test helper's parameter ``existing_tables`` became
  ``get_tables_existing`` while only the ``monkeypatch`` target actually needed
  it. **None of these fails a test**, which is what makes them expensive: the
  local still binds, the parameter still passes, and the suite is green.

**The residual sweep is the step that catches both, and it is mandatory rather
than a courtesy** ``[review]``. It is the only one that reads the tree *after*
the edit, so it sees the call site the grep never showed and the local the sed
should not have touched. **Three** properties are load-bearing, and the third has
been learned twice:

#. it runs over **every** renamed name;
#. its output is **not truncated** -- no pager, no ``head``, no editor match
   limit, and the full output read. This is now the third instance recorded here,
   so it is prescriptive rather than descriptive: a ``head -30`` on a binding
   grep hid three ``on_stop`` call sites in ``addons/bus``, and a capped sweep
   reproduces the first failure while claiming to check for it;
#. it runs over the **whole checkout**, never over the tree you swept. Scoping it
   to your own package is the natural thing to do and is exactly what hides a
   cross-package binding: a sweep confined to ``odoo/service`` passed clean while
   ``odoo/http/tests/test_request_class.py`` was still setting
   ``_catalogue_cache`` by name, and another session found it as a red test
   rather than the sweep finding it as a survivor. Repo-wide and word-bounded
   (``grep -rn -w``) also finds a ``patch.object`` or monkeypatch target reached
   **by string**, which no import graph does.

Read every survivor and classify it, because a legitimate one looks identical to
a missed one. **The survivor list crosses repository boundaries even when the
rename does not**, and that is the reading a workspace-wide count will not give
you: renaming ``NameManager.has_field`` to ``add_available_field`` left the old
spelling in five files across three repositories, and every one was legitimate --
a local in ``ir_attachment.py``, a local in ``addons/account_tax``, a parameter in
``addons/approval``, and the same parameter twice in ``agromarin``, a repository
the rename never entered at all. **Classify per repository**: where the rename
did not go, the old spelling is supposed to survive and the new name never
appears, so neither half of the check below has anything to say about it.

**It has a complement, and neither half sees what the other does** ``[review]``.
A residual sweep finds an *old* name that survived -- the dropped call site. It
cannot see an over-write, because the over-write leaves no old name behind: the
tree is clean and a local has been renamed. What catches that is a **conservation
count** -- occurrences of the old name at the base revision against occurrences
of the new name at the tip, which must be equal. Count occurrences and not lines
(``grep -o | wc -l``), and count **at revisions rather than in the checkout**,
because a working copy several sessions are dirty in cannot answer the question
at all. The procedure, and the four ways it flags something that is not a defect,
are written up in the knowledge vault at
agromarin-knowledge/reference/dev/verifying-a-rename.md -- named in plain prose
because the doc-link gate resolves paths inside this repository alone.

**A generic name is not renameable by substitution at all** ``[review]``, and the
tell is the same one §2.4.14 uses for stored Python: ask whether the spelling
could belong to somebody else. ``def health(`` matched two ``@route`` handlers on
their way to a connection pool's; a ``.snapshot()``, a ``.due()`` or an ``.age()``
belongs to half the tree. Rename those by reading each site, or leave them.

**A protocol declaration is a binding** ``[review]``. The members declared in
``odoo/orm/_protocols.py`` are pinned in ``model_member_surface_check.py``'s
``KNOWN_MEMBER_SURFACE``, so the pin moves with the rename or the gate fails both
ways. A leading underscore is not evidence that a method is local.

Two shapes a Python-only grep misses: **model methods are called by name over RPC
from JS**, and ``mail``'s mock server reimplements Python members so HOOT can run
without a database; and **a prose pointer in another repository is a binding
nothing greps** -- a search written as call syntax (``._get_path(``) finds every
binding and no prose.

**A checker that asserts a source *string* is a binding with no import edge**
``[review]``, and it is the sharpest form of the sentence above, because the
pointer is executable and still ungreppable. A doc gate reading a module with
``read_text()`` and asserting a literal call --
``assertIn("envs.lookup(envs.key(uid, su, frozen_context))", src)`` -- holds a
binding that no import graph reaches, that no test-by-name finds (the test names
neither the class nor the method), and that quotes a **call** rather than a
definition. Renaming ``_EnvironmentSet.lookup`` reddened it. **Grep the written
form of the call, not only the symbol.** Three mechanisms, one file, none of them
found by a symbol search, and each failing differently:

* an ``assertIn`` over the source **fails as an assertion**, naming the string;
* a ``split()`` on a definition's text -- ``src.split("\ndef _prepare_server(",
  1)[1]`` -- raises **IndexError inside the gate**, naming nothing, so the
  rename presents as a broken checker rather than a broken pin;
* a **regex on a method's shape** pins neither a name nor a call, and holds a
  method still merely by matching it.

**The first is the only one that tells you what happened**, so the failure mode
gets worse as the pin gets cleverer. A pin of any of these kinds moves in the
same commit as the rename or the gate fails both ways.

**Prose divides, and only one half is a binding** ``[review]``. A mention is
free; a **citation an argument rests on** is not, and the difference is whether
the sentence would still be true with the name removed.
``addons/hr``'s ``test_hr_audit_round4`` explains a security property by pointing
at ``base``'s ``_is_escaping_own_record``, and that pointer moves with the
rename. A **changelog** entry does not: the vault records ``odoo_env`` at the
moment it was added, and rewriting it would falsify the record. The costly middle
case is a research ledger citing both a name and a **line number** as the evidence
for a finding -- there the argument survives and its citations rot, which is worse
than either, because the next reader checks the line and concludes the finding was
wrong. **Rewrite a load-bearing citation; leave a historical one; and where a
citation is in a repository you are not touching, say which.**

**A record that may not be edited is a fourth category, and it looks like the
first** ``[review]``. A machine doc citing a method is inside the workspace and
greppable, so a sweep sorts it into *greppable-and-rewritable* and rewrites it.
It must not where the citation is frozen: §1.4 makes a machine-doc figure gated
or **frozen**, and a frozen reading must not be "corrected" to a current value.
``run_job_thread`` and ``spawn_http_server`` (``job_thread`` and
``http_spawn`` until ``fd9562fb53e8``, which rewrote both citations with the
names) are cited in ``addons/base/machine_doc_v1/MODEL_MAP.md`` and
``odoo/tests/machine_doc_v1/conventions.md``. **The discriminator is whether the
document naming it may be rewritten, not whether a grep finds it** -- and the
same phrase answers the vault: §14 makes ``research/``, ``plans/`` and
``workspaces/`` dated records of a moment and ``reference/<topic>/``
maintained-current, so rewrite a ``reference/`` hit and leave the others. (The
decision register that once made an accepted record the paradigm case of this
category was deleted; the category is carried by frozen figures and dated vault
records alone.)

* **Rot is expected of a dated record; inversion is not** ``[review]``. Leaving a
  ``research/`` hit is right where the record's **verdict** still holds against
  the tree -- a REFUTED finding whose four citations have gone stale is a dated
  document being dated. It is not right where the verdict has flipped: a ledger
  row marked PROVEN against a defect somebody has since fixed does not read as a
  stale pointer, it reads as an **open confirmed defect against code that no
  longer exists**. **Check the verdict, not only whether the pointers resolve**,
  and where one has inverted, say so in the record rather than leaving it to read
  as true.
* **This class has no failure signal at all** ``[review]``, which is why the
  sweep's root matters more here than anywhere. A missed call site fails a test;
  a missed XML ``name=`` fails at install; a missed string reaches somebody as a
  red suite. A citation in the vault is read by no test and no gate in any
  repository, so it rots in silence -- and the sweep that would catch it is
  one ``cd`` above where everybody runs it.

**A private method can be reached from outside the workspace**
``[gate doc_restated_counts]``. ``ir.actions.server`` stores **Python source in a
database column**: distinct private method names are reached that way from code
blocks in shipped data files of this repository (census table) -- and the
shipped files are only the half a grep can see, since the field is edited in the
UI. **The question is not public against private, but whether a name is written
down anywhere this workspace cannot rewrite.** ``_for_xml_id`` is the case, and it
is taken: 535 places over 351 files in three repositories, plus a
pre-migration rewriting the name in every column that holds Python. **A rename of
this kind is not finished when the tree is green.**

**And the converse is a measurement, not an omission** ``[review]``. The rule
above is the expensive direction; a sweep of core needs the cheap one too, or it
skips the migration silently and calls that a decision. The test is written down
in ``addons/base/migrations/1.23/pre-migrate_method_vocabulary.py`` and nowhere a
reader of this section would look: stored Python runs under ``safe_eval`` with
``env``, ``record`` and ``model`` in scope and **no import**, so it reaches a
name exactly one way -- attribute access from one of those three roots.

* **A module-level function is unreachable by construction**, whatever it is
  called. That is why the script rewrites methods only and anchors every pattern
  on a leading dot: ``.remove_rows`` is ours and a bare ``remove_rows`` is the
  author's own local, which no rewrite may touch. A closure is unreachable for
  the same reason, one level further in.
* **So is a method on a class no expression from those roots can reach.**
  ``odoo/http``'s renamed methods sit on a ``FilesystemSessionStore``, a
  ``Request`` and an ``Application``; none is a model, and a sweep that says so
  in its commit has discharged the obligation rather than ducked it.

**A shipped migration is not the place to add one either.** The script runs for a
database whose stored version is below its directory, so a rename landing after
the module's version has moved past it needs its own -- ``base`` was at **1.26**
while the vocabulary rewrite sat in **1.23**, and a database at 1.26 will never
run 1.23 again. **Read the manifest version before editing a migration**: an edit
to one already passed is a change nothing will execute, and it reads in review
like a change that will.

**A name assembled at runtime is a schema, not a name** ``[review]``. The caller
computes the name and reaches it through ``getattr``. ``odoo/addons/base`` carries
14 of this repository's 37, on 7 % of its model methods::

    getattr(self, f"_run_action_{self.state}")          ir_actions_server
    getattr(self, f"_auth_method_{auth}")                ir_http
    getattr(self, "_render_" + report_type)              ir_actions_report
    getattr(self, f"_compile_directive_{directive}")     ir_qweb
    getattr(self, f"_postprocess_tag_{elem.tag}")        ir_ui_view
    getattr(self, f"_check_view_tag_{elem.tag}")         ir_ui_view

Three consequences, in ascending expense:

#. **The prefix is frozen.** ``_check_view_tag_calendar`` is not an
   ``@api.constrains`` hook -- it is a key in a table. Check for the ``getattr``
   before believing the vocabulary.
#. **Identical bodies are the design, not duplication.** The *key* carries the
   information and the body only answers, so a duplicate report over ``base``
   needs reading rather than acting on.
#. **Some of them need a migration, not a rename.** Where the variable half comes
   from a *stored column* -- ``ir.actions.server``'s ``state``, extended by every
   addon's ``selection_add`` -- the method name is part of the data, and renaming
   it orphans stored records in every database with no gate, test or import error
   to say so.

**Wearing a dispatch prefix does not make a name a key** ``[review]``. **15**
definitions begin ``_render_qweb_``; exactly **3** are keys, because ``_render``
builds its target from ``report_type``, whose Selection offers three values. **The
set of keys is the enumerable domain of the variable half, never the set of names
beginning with the literal half** -- so a sweep must be able to return "this one
is already right".

Adding a dispatch table is a design decision: it creates a naming contract this
section cannot check. Prefer a registry keyed on data you can enumerate; if you
add one, say so in the dispatcher's docstring, because the ``getattr`` is the only
evidence the targets are not free to be renamed.

**A slot filled by reference is free; only a slot filled by name is frozen**
``[review]``. §2.4.10 says a slot and the method that fills it are one contract,
and that is about *spelling them alike* -- it is not a claim that either end is
immovable. Two shapes read alike at a glance and do not behave alike:

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Shape
     - What a rename costs
   * - ``parser.set_defaults(func=self._install)``, ``atexit.register(cb)``,
       ``signal.signal(SIGINT, handler)``, a ``Callable`` dataclass field
     - **Nothing.** The function object is passed; the name is read once, at the
       line you are editing. Rename it and give it the noun §2.4.6 asks for.
   * - ``getattr(self, shell)``, ``getattr(self, f"_render_{report_type}")``
     - **The name is a key**, and the enumerable domain of the variable half is
       the set of keys (above). Do not rename; leave a comment saying so.

The two sit four lines apart in ``cli/shell.py``: ``_enter_console`` reaches
``ipython`` / ``ptpython`` / ``bpython`` / ``python`` through ``getattr``, so
those four are frozen, while every ``set_defaults(func=...)`` handler in
``cli/db.py``, ``cli/module.py`` and ``cli/i18n.py`` is an ordinary method that
was merely spelled like its subcommand. **The tell is whether the name appears
as a string or as an expression.**

**And a slot's own spelling is a name too.** ``cli/scaffold.py``'s
``NamingConvention`` declared ``parse`` and ``modname``; the two methods that
call them are ``parse_params`` and ``get_module_name``, so the contract was
written twice, once with a verb and once without. ``modname`` also broke §2.4.4
outright -- a bare noun for a ``Callable`` field.

**There is a third row, and it reads as a misspelling** ``[review]``: a slot
filled by **reference** whose Python name mirrors a **wire name written outside
the workspace**. ``ir.ui.view``'s ``_hasclass`` looks like ``_has_class`` with an
underscore dropped, and §2.4.8's predicate family invites the repair. It is in
fact the Python half of ``xpath_utils["hasclass"] = _hasclass`` -- the lxml
extension function that ``//div[hasclass('o_address_format')]`` calls, written in
this repository's XML and in every customer's inherited views. The registration
line passes the object, so the *Python* name is free by the table above; the
**string** is not, and mirroring it exactly is the only thing that keeps the pair
greppable. **Where the two must stay spelled alike and one of them is outside the
workspace, neither moves** -- and since the ``xpath_utils[...] = ...`` line is the
whole of the evidence, say so beside it.

**Bound by name, not by inheritance** ``[review]``. The framework calls a method on
a model it resolved at runtime, and any model defining that name answers.
``ir.actions.report`` calls ``_get_report_values`` on a model looked up from the
report's record: the classes in this repository that implement it (census table)
are related to each other and to the caller by nothing but the spelling.
``res.config.settings`` does the same to ``get_values`` and ``set_values``. None
is declared as an interface, and all three counts stop at this repository while
the contract does not. Before renaming a method whose name looks conventional
rather than invented, grep the *framework* for a bare call of it. **Give a new
one of these an ``AbstractModel`` to inherit, so the contract has a declaration
site.**

**And the key is not the method** ``[review]``. ``report_action`` is a **context
key** as well as a method name, so a text substitution takes the key -- and a
local variable of the same name -- along with the method. The same caution applies
to a field name and a registry string.

**The residual sweep has three clauses, and each covers a hole the other two
leave** ``[review]``. A rename is finished when nothing still names the old
spelling, and establishing that is where four sweeps in one day each went wrong
differently.

* **The root is a glob, never a list of repository names.** ``ls -d
  <workspace>/*/``, not a table in a ``CLAUDE.md``. Such a list is a cache of the
  filesystem, and it is wrong in **both** directions the moment a workspace holds
  a checkout that is *machine-local* -- a spike, a proof of concept, a benchmark
  control -- because no shared document can describe one correctly for every
  machine at once, whichever way it describes it. Omitting a repository is the
  expensive direction, since it tells the next reader the grep is pointless; and
  a shared file asserting that a machine-local checkout is **absent** is worse
  than one saying nothing, because it is a *reason* not to look. Say nothing
  there, and glob at sweep time.
* **Enumerating the repositories you know about is not rooting at the workspace,
  and the list you enumerate from can be the thing that is wrong.** One sweep
  that day ran over five repository names copied out of a layout table -- the
  same document that denied a sixth existed -- so it inherited that document's
  blind spot, and no care in running it could have recovered. **A rule that names
  repositories reproduces the defect it exists to prevent, one document further
  down**: write the glob, and do not enumerate even as illustration.
* **The filter is nothing.** Not ``--include=*.py``, not ``--include=*.rs``.
  ``odoo/db/README.md`` is 59 KB of package documentation naming two renamed
  methods, **inside the package being swept**, and a Python-only glob misses it
  without ever leaving the repository.
* **Classify against the embedded-interpreter sites, and find those first.** A
  hit is prose or it is a call, and nothing about the file extension says which.
  Locate the sites before reading any hit::

      grep -rn 'from_code\|py\.run\|py_run!\|include_str!' --include=*.rs

  A hit inside one of those strings, or inside a file an ``include_str!`` pulls
  in, is a **call**; a hit outside every one of them is prose.

**And run the sweep in the other direction, because all three clauses above reach
only your own renames** ``[review]``. Each of them starts from an old spelling the
sweeper already knows about, which makes every author responsible for their own
blast radius and leaves the code that *depends* on a name with no defence at all.
Invert it: enumerate what embedded or generated code **depends on**, and confirm
each dependency still resolves. For embedded Python -- extract the string
constant, ``ast.parse`` it to prove it is still valid, collect every private
attribute it reaches, and check each of them against the tree it runs against.

* **The two directions fail differently, and only the inward one scales.** The
  outward sweep catches a rename **whose author ran it**; the inward check
  catches a rename **by anybody**, including a contributor who has never read
  this section and a tree no suite covers. The break the third clause records
  would have been caught by the inward check without anyone knowing a rename had
  happened.
* **It belongs to the dependent, not to the sweeper**, which is what takes it out
  of the "rule someone has to remember" class: run it from the dependent's own
  test suite and it is a test, not a discipline. Embedded source that no compiler
  and no import graph reaches is exactly the code that owes one, because nothing
  else it is written in will notice.

**The third clause is owed to a break, not to an argument** ``[review]``. A Rust
proof of concept beside this checkout held Python source in a raw string
constant, executed two hundred lines below it by ``py.run``, and one of those
lines called a private ORM method by name. Renaming that method left the line
raising ``AttributeError`` with nothing in the workspace able to say so: a
``.rs`` file no Python scan reads, a string literal no Rust tool reads, and an
FFI ``eval`` that leaves no import edge in either language. Not a naming gate,
not a type-checker, not a test tier, not ``grep -r --include=*.py``.

* **The shape generalises, not the repository.** Any interpreter reached by
  ``eval`` over a string is this blind spot, and the ``safe_eval`` of stored
  Python that the migration rule above exists for is the same class one language
  in. Neither is reachable from an import graph, which is what every other
  mechanism in this section relies on.
* **Same tree, same sweep, two severities.** Four other renamed names sat in that
  checkout as a README line, two ``///`` doc comments and a docstring, and *were*
  only prose. The one difference is whether the name landed in a comment or
  inside the executed constant. **A scan that cannot detect the failing case is
  not evidence about the passing one** -- and the check that cleared the four was
  ``--include=*.py``, which could not have found the fifth had it been there.
* **A rule that holds only when its author types the shorter command is not a
  rule yet.** Three sweeps that day cleared that tree, every one because its
  author happened to omit ``--include`` rather than because anything required it;
  the fourth did not, and the fourth is the one that found the break.
* **Count the sites with the grep, never by eye.** Three readings of one such
  tree within an hour produced three different totals, each undercounting by a
  different file, and every reader had already looked at the code. **No figure is
  given here on purpose**: a machine-local tree is outside every suite, so a count
  would be neither gated nor re-derivable (§1.4) -- on another machine it
  re-derives to nothing -- and the disagreement is an argument for running the
  command, not for recording its answer.
* **A verification that does not cover the file you edited is not evidence
  about it** ``[review]``. This is the class; the three bullets under it are its
  mechanisms. **The denominator that matters is not how many tests ran but how
  many touched the line you changed** -- a run that never held the file, a
  baseline that ran none, and a suite that ran plenty and never entered the
  method are one defect at three scales. Not a caution about carelessness:
  every instance has been a real measurement, honestly taken, pointed at the
  wrong tree, and each of the four in one afternoon was made by an author who
  had just read the previous one. **Distinguish the two halves, because only
  the first is dangerous**: quoting a suite that does not cover the file
  *asserts something false and reads as verification*, while running no suite
  asserts nothing and is visible as such.
* **The suite that covers the file is rarely the one already in your hands**
  ``[review]``. A framework unit run gets quoted because it is what a §2.4 sweep
  has open, while the file just edited sits in an integration suite that is in
  no ``testpaths`` and runs only when named (§6). **Name the suite that covers
  the files in your diff, and check that it runs them.** At repository scale it
  is sharper still: a core change whose only failure surfaces through
  ``enterprise/`` is invisible to every routine suite in this workspace,
  because nothing runs ``enterprise``'s.
* **A mock attribute is a binding that silently ACCEPTS the rename**
  ``[review]``. The sharpest mechanism, because it is the only one that leaves a
  **green test** rather than no test. A ``MagicMock`` absorbs any attribute, so
  a stale ``m.old_name.assert_called_once_with()`` raises nothing -- it records
  zero calls and fails on the *count*, and an assertion weak enough to ask only
  ``assert_called()`` would not fail at all. **Neither half of the check above
  reaches it**: a residual sweep finds the old name and cannot tell a stale mock
  assertion from a legitimate use of a common word, and a conservation count
  cannot see it because a mock attribute has no definition anywhere -- both
  spellings count "correctly" while the assertion asserts nothing. Only running
  the test finds it.
* **Read the denominator, not only the failures — a run that executed no tests
  is not a green run** ``[review]``. The mechanism with no tell, and it defeats
  the habit the rules above teach. Comparing failing *sets* rather than counts
  is right (§8's baseline diff exists for it), and **a set of size zero passes
  that comparison silently**: a baseline whose log is ``No such file or
  directory`` and ``EXIT=127`` reports zero failures because it ran zero tests,
  and against it every real failure at HEAD reads as a new regression. One
  session hit it from a relative interpreter path that stopped resolving when
  the shell's directory moved (§5 warns against spelling the interpreter
  relatively, and this is what it costs). **A baseline owes a test count before
  it is allowed to mean anything**, and the asymmetry is what makes the check
  worth running: **a non-empty failing set proves the run happened, an empty one
  proves nothing**. So the denominator is load-bearing exactly when the
  comparison comes back clean -- which is precisely when nobody looks at it.
* **An extractor is a measurement instrument, and it is the one thing nobody
  baselines** ``[review]``. The three above are faults in the *run*; this one is
  a fault in the tool you read the run with, and it is the only one of the four
  that can make two wrong answers **agree**. A pattern that silently drops part
  of its own key produces a clean diff between two equally broken sets, which is
  indistinguishable from the sets matching. Three ``grep -oE`` instruments in
  twelve hours: one whose character class stopped at a space, collapsing every
  ``Subtest <method> (param=…)`` line to the bare word ``Subtest``; one that
  required a dot and dropped a ``setUpClass`` line entirely; and one keyed on
  ``Starting Test`` that assumed every class is named ``Test*``. **Check the
  instrument against a number the run already reports** -- the started count
  against ``of N tests``, the extracted set size against the raw line count --
  *before* comparing two runs with it. The third instrument was used to convict
  a run of truncation that had in fact completed, and the second survived only
  because the four logs it was pointed at happened to contain no subtests. The
  check works because **``of N tests`` and the ``Starting`` lines have two
  independent producers** -- the result object counts what it collected, the
  logger prints per test -- and two independent producers of one quantity is
  what makes either usable as a baseline for the other. **Where no such second
  number exists there is nothing to check the instrument against, and the only
  remaining defence is a second reading by someone else.**
* **``2>/dev/null`` on a recursive search hides the roots that did not exist**
  ``[review]``. The four above fail in silence -- no tool ever says anything. This
  one is the opposite and is worse for it: the tool diagnoses the problem
  precisely, **once per missing root, by name**, and the redirection everybody
  types out of habit throws the diagnosis away. A residual sweep run from a
  checkout rather than from the workspace named six roots of which five did not
  resolve; ``grep`` emitted five ``No such file or directory`` warnings on
  **stderr**, the sweep covered one root, and it printed nothing -- which is
  exactly what a clean sweep prints. **A search is only over the roots that
  resolved.** Redirect stderr somewhere you will read it, or check that every
  root exists before searching; suppressing it silences the one instrument in
  this section that announces its own failure.

  **The redirection is one spelling of the habit, not the habit.** A second
  sweep, written after this rule was drafted, merged the channel and then
  filtered it -- ``2>&1 | grep -v "^grep: "`` -- which discards the same warnings
  while reading as tidying rather than as suppression; ``2>&1 | tail`` does it by
  position, since the warnings come first. That sweep was sound, but only because
  its author had run ``ls -d */`` beforehand and seen every root. **Prefer the
  check that does not depend on reading the output at all**: assert the roots
  exist, then search.

**A salary rule is stored Python, and no vocabulary migration had rewritten
it** ``[review]``. ``hr_salary_rule.amount_python_compute`` and
``condition_python`` hold code loaded from data files -- often ``noupdate`` --
and agromarin's payslip rules call ``version._get_work_hours_domain(...)`` from
there. Every method-vocabulary migration since base 1.29 rewrote
``ir_act_server.code``, ``ir_actions_server_history.code`` and
``ir_model_fields.compute`` and nothing else, so a rename reaching a name a
rule calls would have raised at the next payslip computation on any database
whose rules had been loaded ``noupdate``. base 1.47 adds the two columns to its
``_STORED_PYTHON`` and the next migration copies that tuple, not 1.29's. The
general rule: **grep the data files of the four repositories for the old name
before writing the migration, and let every ``<field name="code">``-shaped hit
name a column** -- that is how this one was found, by the substitution
reaching two XML files nobody expected.

**A ``default_<field>`` on ``res.config.settings`` is a binding of a FIELD name,
and nothing in the workspace greps it** ``[review]``. ``set_values`` strips its
own prefix and calls ``IrDefault.set(model, <field>, value)``, and this fork's
``ir.default`` raises on an unknown field. ``a0091baeae3`` renamed
``hr.version.mobile`` to ``mobile_subscription`` and left
``l10n_be_hr_payroll``'s ``default_mobile`` behind, so **every** settings save
on a Belgian-payroll database raised *Invalid field hr.version.mobile* --
found by hand and fixed in enterprise ``1e2ff707fd2``. A field rename owes a
search for ``default_<old>`` on every settings model, in every repository,
beside the searches above; the binding is by *convention*, so no ``ref=``, no
``compute=`` and no attribute access carries it.

2.4.15 Signatures
~~~~~~~~~~~~~~~~~

* **An override's signature must match its parent's**
  ``[test_lint test_override_signatures]``. Adding, removing or renaming a
  parameter, or changing its default, is a hard failure. This is what makes
  ``@typing.override`` (§2.9.11) useful rather than decorative.
* **Public methods may not take an ``ids`` or ``context`` parameter**
  ``[test_lint test_naming]``: both collide with the RPC calling convention.
* **A route handler's parameters are named by the route.** ``web``'s
  ``content_common(..., field: str = "raw")`` sits behind a route carrying
  ``<string:field>``: the parameter name **is** the URL segment, and is not
  repaired.

**``field`` is a ``Field``; a field's name is ``field_name``**
``[gate doc_restated_counts]``. A parameter name is the only type statement most
call sites ever see. **98** parameters annotated ``field_name`` are ``str`` and
**0** are a ``Field``, against ``field``'s **132** ``Field`` and **17** ``str``.
One direction is clean; the other is the backlog. The ORM breaks the rule in the
package that states it, and ``lifecycle.py``'s
``_get_placeholder_filename(self, field: str)`` is *bound by name*, so its
parameter name is copied into every addon implementing it.
**A parameter may not borrow a framework key it does not mean** ``[review]``. The
rule above makes a parameter name a *type* statement; where the name is a key the
framework already owns -- ``active_test``, ``context``, ``ids``, ``domain``,
``company_id`` -- it is a **semantic** one too, and borrowing it is worse than a
vague name because the reader does not stop to check.
``cli/i18n.py``'s ``_get_languages(..., active_test=True)`` dropped languages that
are not installed, while the body set the ORM's own ``active_test`` to ``False``
unconditionally two lines above; ``_load_languages`` passed ``active_test=False``,
which reads as *do not apply the ORM's active_test* -- already off -- and meant
the opposite of what it said. It is ``installed_only``. **The tell is a body that
sets the real key to a constant beside the parameter.**

**It is a rule about a name, not about a parameter position** ``[review]``. A
method whose tail is ``_field`` promises a ``Field`` in exactly the way a
parameter does, and the ones that break it are harder to see because the return
is never annotated. ``hr.employee._get_new_hire_field`` returned the string
``"create_date"``; ``hr.version._get_contract_wage_field`` returned a column name
its callers spend as ``self[...]`` and as a ``dict`` key in four modules. Both
now end ``_field_name``. The same reading governs a **collection**: a tail of
``_ids`` promises ids, and ``hr.department.get_children_department_ids`` returned
a recordset -- the tell was that its only call site wrote ``.ids`` immediately
after it, which is the caller repairing the name in place.

**A body that spells the concept the other way is the evidence** ``[review]``,
and it is cheaper than reading the annotation. ``_get_version_periods(field=...)``
raised ``"This field %(field_name)s doesn't exist on this model"``: the message
had the right word and the signature did not. This is §2.4.4's vocabulary-mismatch
check applied to a parameter -- **grep the body for the other spelling before
deciding which one is correct**, because whichever one the author wrote where it
would be *read by a user* is usually the one they meant.

2.4.16 Placement
~~~~~~~~~~~~~~~~

**Naming fixes placement.** The prefix determines the §2.2 section:

.. list-table::
   :header-rows: 1

   * - Name or decorator
     - Section
   * - ``create`` / ``write`` / ``unlink`` / ``copy_data`` / ``default_get``;
       ``@api.model_create_multi``; ``@api.ondelete``
     - ``# CRUD METHODS``
   * - ``_compute_*``; ``@api.depends``
     - ``# COMPUTE METHODS``
   * - ``_search_*``
     - ``# SEARCH METHODS``
   * - ``_inverse_*``
     - ``# INVERSE METHODS``
   * - ``_onchange_*``; ``@api.onchange``
     - ``# ONCHANGE METHODS``
   * - ``_check_*`` (legacy ``_validate_*``); ``@api.constrains``
     - ``# CONSTRAINT METHODS``
   * - ``action_*``
     - ``# ACTION METHODS``
   * - ``_message_*`` / ``_notify_*`` / ``_track_*``
     - ``# MAIL METHODS``
   * - ``_domain_*`` / ``_selection_*`` (field hooks with no banner of their own)
     - ``# HELPER METHODS``
   * - ``_prepare_*`` / ``_get_*`` and other internals
     - ``# HELPER METHODS``
   * - ``_auto_init`` / ``init``
     - ``# HOOKS``

``# <DOMAIN> METHODS`` is the module's business domain, not ``domain=``.

**``action_*`` is a binding, not a family** ``[review]``. The client invokes the
method **by name** -- an XML ``<button name="…" type="object">``, a
``<menuitem action="…">``, a JS call -- so it is not a rule that everything
returning an action dict wears ``action_``; read that way it collides with the
payload family. **The discriminator is who invokes it**: invoked by the client by
name → ``action_*`` / ``action_view_*``; built in Python and returned by something
else → ``_prepare_*`` or its public form. *Frozen reading* (§1.4) at
``2e691b7b90d``, an ad-hoc scanner, not re-derivable: **790** of the **947**
distinct ``action_*`` model methods in the bundled tree appear as a literal
``name=`` or ``action=`` in XML or JS. That sizes the convention, not the
violation.

**The discriminator reads in both directions, and the reading nobody does is the
second one** ``[review]``. *Invoked by the client -> ``action_*``* is the whole
rule, so a method a ``<button type="object">`` names wears the prefix **even
when it returns nothing and does not look like an action**:
``hr.employee.generate_random_barcode`` writes a field and returns ``None``, and
was named by a button in ``hr`` and by an ``xpath`` onto that button in
``hr_attendance``; it is ``action_generate_random_barcode``. The frozen reading
above counts ``action_*`` methods that XML names -- it says nothing about how
many client-named methods are missing the prefix, which is the direction with
the backlog in it. **Search from the XML, not from the ``def``**: every
``name="…" type="object"`` and every ``orm.call`` is a client invocation, and
that list is short enough to read.

**Field wiring beats the name.** A method referenced by ``inverse="..."`` is an
inverse even if it is called ``set_*``; ``compute=`` and ``search=`` likewise pin
their targets. A method used as a field ``default=`` is evaluated at
class-creation time, so it must be defined *above* the field block.
``_search_display_name(self, operator, value)`` is the Odoo 19 hook backing
``name_search``; ``_name_search`` no longer exists.

2.4.17 Cache lifecycle verbs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``invalidate_`` / ``clear_`` / ``reset_`` are not interchangeable ``[review]``.
Cache-coherency bugs are the most expensive class of bug in this system.

.. list-table::
   :header-rows: 1

   * - Verb
     - Means
     - Failure it prevents
   * - ``invalidate_*``
     - Drop values that may be **stale with respect to the database**. A
       *correctness* operation: the data is still wanted, it is no longer
       trustworthy.
     - Serving a value the database has since changed.
   * - ``clear_*``
     - Drop everything held, unconditionally. A *lifecycle* operation --
       teardown, or handing the object to a new owner.
     - Leaking one transaction's or database's state into the next.
   * - ``reset_*``
     - Rebuild derived state **from its source**. Not a drop: the state exists
       again afterwards.
     - Reasoning over a derived structure that no longer matches what derived it.

Pick the verb by what the caller needs, and do not add a fourth. A method that
would honestly need two of them is doing two things.

**Name the fourth, or the ban catches nobody** ``[review]``. A reader checks their
own name against the three rows, does not find it, and keeps it -- which is what
"do not add a fourth" reads as when no fourth is written down. The one people
actually write is ``refresh_``: ``CronSchedule.refresh()`` rebuilt ``_known`` from
``_list_databases()`` and returned it, which is the ``reset_`` row verbatim, and
it is ``reset_known_databases``.

* **These three are reserved for caches, and the borrowing goes outward**
  ``[review]``. A method that drops **rows** is ``_remove_*``: ``_clear_schedule``
  issued a ``DELETE`` against ``ir_cron_trigger`` for triggers already due, and is
  ``_remove_triggers_due``.
* **The verb governs whatever is named after the operation, not only the method
  that performs it** ``[review]``. ``_cache_invalidating_fields`` and
  ``_unconditional_clear_fields`` fed one decision through a local called
  ``clear`` -- one operation, two of the three verbs, in a file that caches
  nothing. They are ``_get_fields_invalidating_always`` and
  ``_get_fields_invalidating_when_cached``.
* **A name in adjective position needs a participle** ``[review]``. The canonical
  read verb has no participle anybody writes, so ``fetched_bundles`` survived
  where the table cannot serve. **Name the state, not the operation**:
  ``loaded_bundles``, on the model of ``BundleWalk.walked``. A **method**
  performing the read is still ``_get_*``.
* **A memoised read is three methods** ``[review]``: an **entry** deciding which
  path to take, a **memoised** wrapper carrying ``@tools.ormcache``, and the
  **body** both reach. The only thing separating them is the caching:
  ``_get_X`` / ``_get_X_cached`` / ``_get_X_uncached``. **The trio may straddle
  the public/private line, and then only the private two move**: ``db/listing``'s
  ``list_dbs`` / ``_cached_catalogue`` / ``_query_catalogue`` is the shape with
  the caching unsaid, and it is ``list_dbs`` / ``_get_catalog_cached`` /
  ``_get_catalog_uncached`` -- the entry keeps its public name, because completing
  the pattern over it would be a public-surface change (§2.4.14) bought for
  symmetry. ``request_class.py`` has the same shape with the cached half in
  ``odoo.http.__all__``, where it cannot move at all.
* **``_cache`` and ``_cached`` are different tails** ``[review]``. ``_cache`` names
  **the cache object** (``_get_view_cache``) at 25 methods; ``_cached`` marks
  **the memoised variant** of the method above it, at 14.
* **``_impl`` names the implementation, which is not a fact about the operation**
  ``[review]``. Every method implements itself; where the suffix appears there is
  a real discriminator left unsaid. The family is at 0 here.

**The three verbs above are the *drop* side, and the fill side is spelled four
ways** ``[review]``. "Do not add a fourth" governs dropping; warming a cache is a
different operation and the table never named it, so the tree grew
``_prefetch_``, ``_warm_``, ``_preload_`` and the cache sense of ``_populate_``
for it. *Frozen reading* (§1.4) at ``45275737cf4``: **12**, **3**, **3** and
**2**. **The canonical is ``_prefetch_``** -- it is the ORM's own word for this
exact operation (``with_prefetch``, ``prefetch_ids``, and ``fetch`` itself),
so the family is already searchable from the framework side. ``populate`` is
**reserved** for the ``odoo populate`` CLI's data generation
(``populate_model``, ``populate_field``), which fills a database and not a cache;
the two senses are why a grep for one finds the other.

* **Warming is invisible to the caller, which is what makes the name the only
  evidence it happened.** A prefetch method returns nothing a caller uses and
  removing it breaks no test -- it costs queries, not correctness. Name it for
  what it warms, so the reason it exists survives the next reader:
  ``_prefetch_rollup_moves``, not a ``_rollup_moves_fetch`` that reads as a
  variant of the walk beside it.
* **The tail is the wrong end for this verb** ``[review]``. Three of stock's
  spelled it there (``_rollup_move_dests_fetch``), which put the *reserved* ORM
  ``fetch`` (§2.4.3) in the one position where §2.4.4's rule cannot see it and
  made the trio sort beside the ``_rollup_*`` walkers they warm rather than
  beside each other.

* **The three bind names whose object is held state** ``[review]``. Read as an
  unbounded reservation the table sends a reader to rename things it was never
  about: ``cli/upgrade_code.py``'s ``FileManager.clear_progress`` (deleted since,
  with the upstream source rewriters) wrote the ``\033[K`` that erases a progress
  line, held nothing, and dropped nothing that could go stale -- and it was a
  published API every shipped ``upgrade_code`` script called, so a rename was
  real cost for no correctness. **The failure column is the scope**: where no
  reader can be served
  a wrong value because the state was kept, the table has no opinion and the
  ordinary vocabulary applies. Transient output is outside it; **rows are not**
  (``_clear_schedule`` above), because a row is state something else will read.
* **``reset_`` promises a source, and a per-owner initialiser has none**
  ``[review]``. The third row is the one a sweep reaches for by reflex, because
  *reset* is the ordinary English word for putting something back the way it
  started -- and that is not what the row says. It says **rebuild derived state
  from its source**, which requires there to be one. ``http/application.py``'s
  ``_reset_thread_state`` ran at the top of every request on a **reused** worker
  thread: it zeroed four counters, deleted ``dbname``, ``uid`` and ``url``, and
  stamped a fresh ``perf_t0``. Nothing is rebuilt from anything, and what it
  prevents is the ``clear_`` row's failure verbatim -- one request's state read
  as the next one's. It is ``_clear_thread_state``. Two readings:

  - **A counter set to zero is a drop, not a rebuild.** Zero is the counter's
    empty value; writing it is how a counter is cleared, and a rebuilt counter
    would have to come from somewhere.
  - **Stamping the new owner's start value is part of handing the object over**,
    not a second operation the method also does. ``clear_``'s row already reads
    *teardown, or handing the object to a new owner*, and the start of the new
    owner's use is that same moment.

* **A chain may not rename the operation at each frame** ``[review]``. The table
  decides a verb by what a **frame does to the state it holds**, so a ``clear_``
  is allowed to be one step of an ``invalidate_``: what may not happen is a
  frame naming itself for the step below it. ``odoo/db`` had four frames for one
  operation -- ``Cursor._invalidate_caches_after_ddl`` calling
  ``discard_cached_plans`` calling ``lifecycle.clear_prepared_cache`` and
  ``TransactionSchemaCache.clear_catalog_facts`` -- which is three of this
  table's verbs plus a fourth the table does not own, for *drop what the DDL just
  made stale*. The leaf was right and is unchanged: ``clear_prepared_cache``
  drops everything psycopg holds prepared, unconditionally, and is a ``clear_``
  by the row above whichever caller reaches it, because a leaf has no reason --
  it has a scope. Every frame that decides **why** owes ``invalidate_``, which
  is what took ``clear_catalog_facts`` to ``invalidate_catalog_facts`` and
  ``discard_cached_plans`` to ``invalidate_cached_plans``. Read a
  chain from the leaf up: **the verb is chosen by the frame, and the reason
  belongs to the frame that has one.**
* **The sibling that stays ``clear_`` is the evidence the rename was right.**
  ``TransactionSchemaCache.clear()`` calls ``invalidate_catalog_facts()`` and
  then drops ``locked_tables`` as well -- a ledger of advisory locks that cannot
  go stale against the database because the transaction holding them is what
  ends. Lifecycle, unconditional, everything held: ``clear_``. **A class whose
  two drops differ in scope and in reason should show both verbs; a class where
  every drop is spelled the same way has not asked the question.**
* **``_discard_`` is not a fourth cache verb** ``[review]``. §2.4.3 reserves it
  for the ``set.discard`` contract -- remove if present, **never raise** -- and
  ``discard_cached_plans`` breaks the second half: it warns, sets
  ``prepare_threshold`` to ``None`` and issues ``DEALLOCATE ALL``, any of which
  can fail. **A reserved verb borrowed for a cache drop reads as a fourth
  member of this table and is measured by nothing**, because the table lists
  three names and a grep for them does not find it.

2.4.18 The ingestion vocabulary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reading an external document into records is one cycle, and this repository
implements it eight times. The census is in
``agromarin-knowledge/research/2026-08-29-document-ingestion-census.md``; the
finding that belongs here is *why* the duplication stayed invisible for so long.
Every implementation spelled the same four operations differently, so no search
and no reviewer could put two of them side by side. ``file_data``,
``DocumentSource`` and ``raw_file`` are one concept under three names, in three
modules, none of which cites another.

**The cycle has five operations, and the stages after them are already
governed** ``[review]``. Mapping values onto a record is a payload operation
(``_prepare_*``, §2.4.7), writing them is a mutation (``_update_*``), checking
them raises (``_check_*``) or answers (``_is_``/``_has_``), and reporting what
happened is a read (``_get_*``). Nothing new is needed for those, and inventing
a verb for them is how a seventh dialect starts.

.. list-table::
   :header-rows: 1
   :widths: 12 15 35 38

   * - Operation
     - Canonical
     - Operand → result
     - Abolished
   * - Acquire
     - ``_download_*`` ``_import_*``
     - a remote service → a document (``_download_``), or → local records made
       from what it returned (``_import_``)
     - ``_fetch_`` ``_retrieve_`` ``_grab_`` (of something remote)
   * - Identify
     - ``_guess_*``
     - bytes → a name for what they are: mimetype, encoding, separator,
       document type
     - ``_sniff_`` ``_detect_`` (of a format)
   * - Unwrap
     - ``_unwrap_*``
     - document → the documents inside it: PDF attachments, archive members,
       one XML split on a repeated tag
     - ``_split_`` ``_explode_`` ``_expand_`` (of a document)
   * - Read
     - ``_read_*``
     - document → **one representation**: rows, text, tree, data, images,
       barcodes
     - ``_parse_`` ``_decode_`` ``_load_`` ``_index_`` (of a file)
       ``_derive_`` ``_interpret_``
   * - Extract
     - ``_extract_*``
     - representations → **candidate field values**, with where each came from
     - ``_digitize_`` ``_mine_`` ``_pull_`` ``_ocr_``

**Acquisition is the step before the bytes are in hand, and it had no verb**
``[review]``. The four operations below it all start from a document the server
already holds; getting one from a bank, a tax portal or a payroll service is a
separate step that crosses a network boundary, and it was spelled ``_fetch_`` in
forty-odd places — the word §2.4.13 keeps for the ORM's own read. Name what comes
back, not the trip:

* **``_download_*``** when the result is a document — bank statement files,
  invoice PDFs and XML. The direction is *this server takes from a remote
  service*; serving a file to a browser is a route or an ``action_``, never this
  row, even though public ``download_*`` methods do both today.
* **``_import_*``** when what comes back becomes **local records** — vendor bills
  from a tax portal, transactions from a bank feed, payruns from a payroll
  service. ``_import_`` already means external data in as records for 108
  definitions, and remote acquisition is the same operation from a further source.
* **``_get_*``** when the remote answer is **not stored** — a status, a
  participant lookup, an access token held only in a cache. Crossing a network does
  not change the Read row (§2.4.7); a cache write is not a record.

A body that downloads **and** imports is ``_import_``, because the records are the
product and the document an intermediate. A cron wrapping one keeps its namespace:
``_cron_import_*``.

**The Read/Extract line is the one that keeps being crossed** ``[review]``, and
crossing it is what made the eight implementations impossible to compare.
``_read_*`` knows formats and no business; ``_extract_*`` knows a document type
and no formats. A method doing both is why ``_parse_bank_statement_file``
cannot be reused by anything that is not a bank statement, though half of it is
an OFX reader. Split it, and the half that reads becomes everyone's.

**The nouns matter more than the verbs here** ``[review]``, because a
concept named three ways is a concept nobody can grep for.

.. list-table::
   :header-rows: 1
   :widths: 26 16 58

   * - Concept
     - Canonical
     - Abolished
   * - the bytes, plus what they are
     - ``document``
     - ``file_data`` ``source`` ``raw_file`` ``blob`` ``payload`` ``upload``
   * - one derived view of a document
     - ``representation``
     - ``format`` ``rendering`` ``form`` ``view``
   * - document → representation
     - ``reader``
     - ``parser`` ``decoder`` ``loader`` ``indexer`` ``handler``
   * - representations → values
     - ``extractor``
     - ``decoder`` ``strategy`` ``engine`` ``provider`` ``digitizer``
   * - what a document type must yield
     - ``schema``
     - ``spec`` ``shape`` ``definition`` ``template``
   * - a requirement between its fields
     - ``rule``
     - ``constraint`` ``invariant`` ``validator``
   * - one strategy's proposed value
     - ``candidate``
     - ``guess`` ``suggestion`` ``proposal`` ``hit``
   * - values plus provenance, against the schema
     - ``result``
     - ``output`` ``values`` ``data`` ``payload``
   * - the ordered run of extractors
     - ``cascade``
     - ``chain`` ``pipeline`` ``waterfall`` ``fallback``

``attachment`` is **not** a synonym for ``document``: it is the ORM record that
may carry one. A function taking bytes takes a ``document``; a method reaching
for ``self.attachment_id`` is doing acquisition, which is the one stage that
legitimately differs per consumer.

**Four of these are mechanical and the rest are not** ``[ratchet naming]``.
``naming_vocabulary.py`` carries ``digitize``, ``interpret``, ``derive`` and
``sniff``: each has no second sense in this tree, so a name containing one is
wrong wherever it appears. The others keep a legitimate meaning elsewhere and a
stem test would flag it, so they are ``[review]`` and widen no gate:

* ``_parse_`` is **reserved for a scalar**: one string in, one typed value out --
  ``_parse_float_from_data``, ``_parse_datetime``, ``parse_version``. Reading a
  *file* is ``_read_``, whatever its format.
* ``_decode_`` is **reserved for an encoding with a key or a scheme** --
  ``_decode_connect_token``, ``_decode_certificate_for_be_dmfa_xml``. A document
  in a file format is not encoded, it is written; reading it is ``_read_``.
* ``_load_`` is **reserved for the ORM operation and for module loading**. It is
  the most-borrowed verb in the tree, which is exactly why reading a file must
  not borrow it. The reservation is against **reading a document** under this
  verb; filling held state from an authoritative source is a third legitimate
  sense and keeps it (``cli/obfuscate.py``'s ``_load_field_catalog`` queries
  ``information_schema`` and indexes the result). Read the row as a list of what
  the verb may mean, not as a list of two.
* ``_index_`` is **reserved for building an index** -- a mapping from key to
  member, ``_index_by_grouping_key``. Producing the text a search index will
  hold is ``_read_``: ``_index_pdf`` returns a string, indexes nothing, and is
  ``_read_pdf_text``.
* ``_split_``, ``_scan_``, ``_detect_`` and ``_ingest_`` each name something real
  away from documents -- splitting a string, sweeping a directory, finding a
  bounce in a mail, accepting a bulk payload from a device. Against a document
  they are the canonical above.

**A registry, not a dispatch table** ``[review]``. A ``mimetype``-keyed ``dict``
naming methods is the shape every one of the eight grew independently, and it is
what makes a format unaddable from outside the module. A reader declares the
mimetypes it accepts and the representation it yields, and registers itself;
``get_readers`` is the only dispatch. The same holds for extractors, which
additionally declare what they cost, so the cheap one is tried first.

2.4.19 What a Python-only reading misses
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

§2.4.13 says the vocabulary reaches further than the gate, and §2.4.14 says a
rename carries its bindings. Two bindings sit in the gap between them -- a
caller and a data column -- and a sweep that reads ``def`` statements finds
neither. Each has cost a rename that looked finished. The third thing in that
gap is a *definition* rather than a binding, and it is §2.4.13's fourth
ungoverned population.

**A raising validator is a legitimate public contract** ``[review]``, and
§2.4.4's signature evidence does not reach it. That rule reads a return of
recordsets, callables or exceptions -- anything that will not serialise -- as
proof the missing underscore was an oversight. **A method that returns nothing
at all serialises perfectly**, and where the whole contract is the ``raise``,
the client calls it precisely to receive the error. ``hr.version``'s
``check_contract_finished`` takes no argument, returns nothing and only raises;
``button_new_contract.js`` awaits ``orm.call("hr.version",
"check_contract_finished", …)`` and lets the ``ValidationError`` surface as the
dialog. Both it and ``hr.employee.check_no_existing_contract`` are correctly
public, and the reading that would have privatised them is the signature.
**Settle it with the caller, and look for it in ``static/src`` before the
signature**: ``git grep -n '"<name>"' -- '*/static/src'`` costs one command and
answers the question the signature only guesses at. The evidence in §2.4.4 is
sound in one direction -- a non-serialisable *parameter* still proves the RPC
call cannot happen -- and unsound in the other.

**A method name can live in a database column that no upgrade rewrites**
``[review]``. §2.4.14 has the case -- ``ir.actions.server`` stores Python source
-- and this is the test it does not give: **``noupdate``**. A server action or
cron declared in an updatable data file is rewritten on every module upgrade, so
renaming its target is an ordinary greppable rename. One inside ``<data
noupdate="1">`` is written at install and never again, so the old name survives
in every database that already has it and the rename needs a migration script.
``hr``'s ``notify_expiring_contract_work_permit`` is named by
``model.notify_expiring_contract_work_permit()`` in an ``ir.cron`` under
``noupdate="1"``: a green tree there means nothing, and it is left as found for
that reason and not because the name is right. **Check the flag on the enclosing
``<data>``, not the file**, and §3.9 for what the flag does and does not protect.

**A nested function is the population §2.4.13 counts as ``nested_helpers``**,
and the reason to read it there rather than here is that the three ungoverned
populations only mean anything together. Two things about it belong to this
section, because they are about the *reading* rather than the count: it is
invisible to a reviewer as well as to the gate, since it appears in no outline
and in no search for ``^    def``; so when sweeping a file, **grep ``\bdef ``
and not ``^    def``**. ``hr``'s was ``date2datetime`` (§2.4.5).

**The largest thing a Python-only reading misses is the other language**
``[review]``. §2.4 governs ``def``; §4.2 gives JavaScript ``camelCase``, the rule
that a string naming a Python method must match it exactly, and no verb
vocabulary at all. So every row of §2.4.3, every reservation and every
discriminator stops at the language boundary, and ``addons/web/static/src`` is
**862** files on the far side of it. *Frozen reading* (§1.4) at ``f5d34bc3c95``:
**332** definitions there open with a verb the table abolishes or §2.4.20 lists
as a synonym -- ``make`` 75, ``build`` 71, ``validate`` 58, ``delete`` 48,
``fetch`` 30, then a long tail.

**Most of that 332 is not a defect list, and the reason is specific to the
language rather than to sample size**: the three largest entries are *framework
contracts wearing an abolished spelling*, so a mechanical sweep would break
running code rather than merely misname it. ``validate`` is an OWL prop-schema
key -- ``props = { x: { validate } }`` -- which OWL reads by name. ``delete`` is
the ``Map``/``Set`` contract and a reserved word, so §2.4.3's reservation binds
harder here than in Python. ``make*`` is this codebase's factory idiom, from
``makeEnv`` down. ``fetch`` is ``window.fetch``, and §2.4.3 already reserves it.
**A gate banked on that population would be a floor of exemptions**, which is
§2.4.20's word list with a JSON file around it.

**So the rules that cross the boundary are the ones whose discriminator is a
body, not a spelling.** *Removes entries from a collection* is the Removal row in
any language, and nine names in ``web`` were renamed on exactly that reading: the
``prune`` family, ``purgeStorage``, ``_sweep`` and ``deriveFromApplied``. None of
those four verbs has a JavaScript idiom behind it, which is what separates them
from ``make`` and ``fetch``. **Ask what the body does, never what the token looks
like** -- a head-token scan manufactures findings of its own, and two of this
one's were ``controlPanelSlots`` (the noun *control panel*) and
``browser.location.assign`` (the DOM API).

**An OWL template is JavaScript's stored-Python column, and it is the binding
that bites** ``[review]``. §2.4.14's case is ``ir.actions.server`` holding Python
that no grep of ``def`` reaches; the JS twin is a template calling a method by
string -- ``t-on-click="foo"`` -- which no linter resolves and no import graph
shows. It shares the property that makes the server-action case expensive: the
rename succeeds, the suite passes, and the call site fails at runtime somewhere
the author was not looking. **Grep the name in ``*.xml`` before renaming a
component method.** Doing that by hand nine times is the right cost and it does
not generalise, which is the third independent argument for treating this
population as a candidate list.

2.4.20 Synonyms, and the verbs the table does not print
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**A zero on the abolished table is evidence the sweep ran, not evidence the
operation is gone** ``[review]``. *Frozen reading* (§1.4) at ``75ef0eec641``, an
ad-hoc census over §2.4.3's population: ``_fill_``, ``_purge_`` and ``_derive_``
stand at **0** model methods each -- three of the table's own entries, drained to
nothing. The operations they name are not gone. ``_determine_`` stands at **6**
definitions, ``_populate_`` at **4**, ``_prune_`` at **2** and ``_seed_`` at
**2**, and every one is a row of the table under a word nobody listed: populating
is filling, pruning is purging, determining is deriving, seeding is creating.
``naming_vocabulary.py`` matches the literal token by construction, so a synonym
is invisible to it -- and the entry it *can* see reaches zero looking like a
finished family.

**So read the table as families, not as a word list** ``[review]``. Where a verb
is not printed there, do not conclude it is ungoverned: ask which row's
*discriminator* the body satisfies, and take that row's canonical. The four above
are ``_update_``, ``_remove_``, ``_read_`` and ``create``. §2.4.12's ``_toggle_``
is the same reading arriving from the other side, and §2.4.8 is this one in
reverse -- a name wearing a listed verb that turns out not to belong to its
family.

**That reading is a gate in every repository now, not advice**
``[ratchet naming]``. ``naming_vocabulary.py``'s ``ABOLISHED`` carries the
synonyms beside the printed rows -- ``populate`` and ``tweak`` (Mutation),
``prune`` and ``sweep`` (Removal), ``seed`` (``create``), ``scan`` (``_read_``),
``detect`` (Predicate, or Read where the body returns what it found),
``determine`` and ``calculate`` (Read), and ``synchronize`` in both spellings
(the reserved ``_sync_``, or ``_prepare_`` under a payload suffix) -- and
``assemble``, ``craft`` and ``forge`` join the Payload verbs on the same terms
as the four, flagged whatever the tail. They were a core-only reading in
``naming_core_vocabulary.py``'s ``SYNONYMS`` until 2026-09-09, on the argument
that widening the shared table would move the addon floors by names nobody had
read; they were read, one repository at a time, and the counts are in
§2.4.13's table. **What the table leaves out is argued in the same comment as
what it holds**, because a synonym table nobody can see the edge of is a word
list again -- ``refresh`` stays core-only, because in ``addons/`` the same word
is an OAuth *refresh token* and ``REFRESH MATERIALIZED VIEW`` and a name cannot
tell either from §2.4.17's cache verb; ``reap`` and ``probe`` are terms of art
from a layer below on §2.4.3's *reserved, not abolished* terms; ``emit`` is
``logging.Handler``'s contract and renaming it unhooks it in silence;
``collect`` needs a discriminator the shared table does not have (most of
core's accumulate into a caller's container and return nothing, which is not
the Read row -- the core gate's ``accumulate`` rule reads the body for it); and
``locate`` reads zero in every addon tree and five in core, where
``locate_node`` is the view-inheritance spec resolver, so a row for it would be
five allowlist entries and no tightening.

**The edge of the table is now measurable, and ``sanitize`` is the row it is
missing** ``[review]``. The argument above is that a synonym table nobody can see
the edge of is a word list again; the edge is the set of leading tokens the
vocabulary governs by nothing, and it is **2,333** tokens over **18,148**
production definitions (§2.4.4). Read the large end of it against §2.4 as a
whole, and the section already rules on most: ``generate`` in §2.4.7, ``parse``,
``split`` and ``extract`` in §2.4.18, ``find`` in §2.4.11, ``convert`` in §2.4.5,
``filter`` and ``iter`` against the receiver-shaping rule of §2.4.22. **Two
spellings are ruled nowhere and name one operation between them**:
``_normalize_`` at **75** definitions and ``_sanitize_`` at **56**, both
reshaping a value and returning it -- ``_sanitize_number`` beside
``_normalize_iban_acc_number``, ``_sanitize_vals`` beside ``_normalize_rfc``.
**``_sanitize_`` is abolished**, because *sanitise* names a **motive** -- the
input is untrusted -- and a motive is not an operation. That is also why it
cannot be swapped for one word: read against their bodies, the 57 definitions
wearing it were doing **five** different things, which is the cost of a motive
verb stated as a count.

.. list-table::
   :header-rows: 1
   :widths: 24 30 46

   * - Body
     - Canonical
     - Example
   * - reshapes a value
     - ``_normalize_``
     - ``_sanitize_ean`` → ``_normalize_ean``
   * - returns a subset
     - ``_filter_`` (§2.4.22)
     - ``_sanitize_fetch_params`` → ``_filter_fetch_params``
   * - mutates in place
     - ``_update_`` (§2.4.12)
     - ``_sanitize_configuration`` → ``_update_configuration``
   * - builds a payload
     - ``_prepare_`` (§2.4.7)
     - ``_sanitize_payload`` → ``_prepare_task_vals``
   * - raises
     - ``_check_`` (§2.4.8)
     - ``sanitize_model_name`` → ``check_model_name``

**Two neighbours are reserved rather than abolished, on §2.4.3's terms.**
``escape`` is the operation that makes a value inert **inside a target syntax**
and is not a normalisation -- prefixing a spreadsheet formula trigger with an
apostrophe changes the value so the cell does not execute it, and
``_escape_export_cell`` says which syntax. **HTML sanitisation keeps the word**:
``libs/text/html``'s cleaner removes scripts, event handlers and foreign
attributes, which destroys content on purpose, and *sanitise* is that layer's
term of art exactly as ``_drop_`` is SQL's. The test between them is whether the
output is the same value in another form (normalise), the same value made inert
(escape), or **less** than the input on purpose (sanitise, and say what it
strips).

**``_save_`` is the reserved-table case, not a new row** ``[review]``. §2.4.3
reserves ``read`` / ``write`` for a method whose object is a **file**;
``_save_`` at **70** definitions is the same contract wearing a third word, and
the census caught the pair that proves it -- ``_save_label`` and ``save_label``,
byte-identical bodies, the **only** duplicate group in the tree that the
abolished→canonical substitution merges. Where the object is a file the verb is
``write``; where it is a record it is ``create`` or ``_update_``; where it is an
attachment row, say which.

**A predicate prefix suspends the infix rule, and that is not a fudge**
``[review]``. §2.4.4 flags a verb behind a noun because the noun hides it from a
``classify`` that partitions on the first token. Behind ``is_`` / ``has_`` /
``can_`` / ``should_`` there is nothing hidden: a predicate does not perform the
operation its tail names, it answers a question **about** it, so the verb is the
subject. ``can_scan_identity`` asks whether a field's cache admits an identity
scan, and renaming its middle token renames the question rather than the
operation. The carve-out is in the shared gate's ``infix_abolished_verb``, and
the four definitions it protects sit on one module.

**Two of the gate's rules read the body, because their discriminator is a claim
about behaviour** ``[gate naming_core_vocabulary]``. Every other rule in it is a
statement about spelling and answers from the name; these two cannot.

* **A ``collect_*`` is the Read row exactly when the value it returns is the
  value it made.** Where it fills a container it did not create -- a parameter,
  an attribute of its receiver, a closure variable of the function around it --
  the product is that container and the return is bookkeeping: a loop variable, a
  recursion handle, a token-stream state. That is the Addition row acting on
  somebody else's object, and ``_get_`` would be a lie about where the answer
  comes out. The distinction is not cosmetic: of core's twenty-six
  ``collect_*``, eleven return a value and only **seven** own it, so a rule that
  stopped at *returns something* would have been wrong four times out of eleven.
  ``_collect_split_pdf_streams`` and ``_get_saved_attachment_streams`` sit a
  hundred lines apart in one file and are now spelled differently, which is the
  rule speaking rather than an inconsistency.
* **A ``check_*`` that returns instead of raising is the Validation row's blind
  spot**, which the paragraph above already argues for the public spelling. The
  gate's proxy is mechanical -- the body returns a value and raises nothing --
  and it **is** a proxy: a check whose failure path is a helper's raise reads
  from here exactly like a read. ``safe_eval``'s ``check_values`` and
  ``mail``'s ``ir_mail_server._check_hostname_callback`` are that shape and are
  argued into the allowlist rather than renamed. **A rule whose test is one
  frame deep should say so in the allowlist rather than in a comment nobody
  reads.**

**The prefix that survives a ``check_`` is not always a predicate**
``[review]``. Asking *what row does the body satisfy* rather than *what is the
opposite of check* is what separates four answers a single substitution would
have collapsed into one. ``odoo/tools/config.py``'s six were ``optparse``
**type checkers**, reached through a ``TYPE_CHECKER`` dict mapping a type name
to a callable -- nothing dispatches on the spelling, and each takes one string
and returns one typed value, which is §2.4.3's reserved ``parse``.
``view_validation``'s four return a **list of warning strings** and are
``get_*_warnings``. The five in ``libs/filesystem/mimetypes.py`` return a
**mimetype or a falsy** and are ``_get_*_mimetype``. Only ``libs/barcode.py``'s
answered a question about its subject with a ``bool``, and only that one became
a predicate.

**A whole-word substitution is a claim that the name is unique, and it is
usually false** ``[review]``. §2.4.20 makes this point about a name that is also
an XML id; the commoner case is a second definition of the same name elsewhere
in the tree. ``config._check_path`` is an ``optparse`` type checker and
``ir.actions.actions._check_path`` is an ``@api.constrains`` that raises: one is
this rule's finding and the other is the rule working correctly, and one
``sed`` on ``\b_check_path\b`` renamed both. **Read the definition sites a
substitution will touch before running it, not the call sites** -- there were
three files' worth here, and no test would have caught it, because the
constraint went on working under its new name.

**A producer's prefix is a claim about the return, and the same body test
settles it** ``[gate naming_core_vocabulary]``. ``_get_`` is the Read row and
``_prepare_`` is the Payload row; both are promises about what comes back, and
neither survives a body that returns nothing. ``Field.prepare_setup`` set
``self._setup_done = False`` and ``registration._prepare_setup`` discarded a
class's memo attributes -- both **reset** state for the setup phase and produce
nothing, and both are ``reset_setup``. ``_prepare_missing_trees`` filled
``state.trees`` and is ``_add_missing_trees``.

* **Two exclusions, and each is a class of name rather than an exception.** A
  producer that always **raises** is refusing on behalf of a name it did not
  choose: ``ir.qweb``'s restricted rendering mode declines ``_get_field``,
  ``_get_widget`` and ``_get_asset_nodes``, and renaming those unhooks the
  override from its parent. A Protocol member or an ABC stub has no body to
  read at all. Neither is in the allowlist, because neither is a judgement --
  they are what the rule means.
* **The one that IS a judgement is in the allowlist**, and it is the shape no
  AST can see: ``profiler.py``'s tracing collector overrides
  ``Collector._get_stack_trace`` and returns ``None`` because it has none to
  give. It calls no ``super()``, so ``_overrides_same_name`` cannot find it.
* **The converse claim is §2.4.11's**: a producer that **creates** records is
  not describing them. ``properties.base.definition``'s
  ``_get_definition_id_for_property_field`` searched, created when it found
  nothing, and returned the id, under a name promising only a read; it is
  ``_get_or_create_definition_id_for_property_field``.
* **``write`` is deliberately not evidence of an ORM write, and its absence is
  the rule.** §2.4.3 reserves ``read``/``write`` for a method whose object is a
  **file**, so a call spelled ``write`` is as likely to be the filestore --
  ``ir.attachment._prepare_content_vals`` ends in
  ``backend.write(data, checksum)`` and is a correct payload builder.
  ``Command.create([...])`` is excluded for the mirror reason: it **is** a
  one2many payload, so matching the attribute name alone would flag the
  canonical use of the canonical prefix. ``create`` and ``unlink`` on anything
  else have no such twin.

**``determine`` is in the synonym table after all, and the case for holding it
out was wrong in an instructive way** ``[gate naming_core_vocabulary]``. It was
excluded twice on the grounds that core's population is a *dispatch* question,
which §2.4.9 leaves provisional -- and that reading came from the two members
that dispatch, not from the family. Read whole, the nine split cleanly on the
test this section already uses: four **return** a value and are the Read row
(``Field.determine_domain`` returns a ``Domain`` and is ``get_search_domain``,
``determine_group_expand`` returns groups and is ``get_expanded_groups``, both
``_determine_fields_to_fetch`` are ``_get_fields_to_fetch``), two **perform**
one and take the operation's own verb (``determine_inverse`` is
``apply_inverse``, which is the word ``_create_apply_inverses`` in the same
package had been using for it all along), one **assigns** and is ``set_key``,
and the dispatcher itself is ``call_hook``. **A family that looks
undecidable often contains two families**, and the census that says so is
reading the bodies rather than the names.

**``_show_`` is a fourth predicate prefix, on §2.4.8's terms** ``[review]``, at
**16** definitions under **12** names. It answers a question about the subject
and returns a ``bool``, so it belongs to ``_is_`` / ``_has_`` / ``_can_`` with the
modality moved into the tail exactly as ``_should_``'s is: ``_show_profitability``
is ``_is_profitability_shown``. It is out of ``ABOLISHED`` for the reason that row
gives for ``_should_`` -- an entry prints one canonical target and this family has
three.

**A ``_show_X`` beside a ``_show_X_helper`` is two questions under one name**
``[review]``. The pair asked *is there profitability to show* and *may this user
see the analytic breakdown*: the second is not a helper of the first, it is a
different subject, and ``_helper`` is §2.4.17's ``_impl`` under another word -- a
suffix standing where the discriminator was left unsaid.

**A public ``check_*`` that returns instead of raising is the Validation row's
blind spot** ``[review]``. §2.4.8 makes the point for the unbound *private*
spelling; the public one is where it survives, because no ``@api.constrains``
binds it, no gate reads it, and the missing underscore keeps it out of every sweep
aimed at internals. ``project.project.check_features_enabled`` returned
``dict[str, bool]``, never raised, and was called over RPC by two form
controllers: it is a read, and it is ``get_features_enabled``. **Ask what the
method does on failure before believing its prefix** -- where the answer is
*returns something*, the prefix is wrong whatever the underscore. The vocabulary
already licenses the public spelling, so the rename owes the workspace-wide
rewrite and nothing more. **§2.4.19 is the converse and must be read with this one**: a public
``check_*`` that returns nothing and *only* raises is correct, and privatising it
would break the client that calls it to receive the error.

**``_refresh_`` is the fourth cache verb §2.4.17 declines to add** ``[review]``,
at **15** definitions under **13** names. It names neither the drop nor the
rebuild, so it cannot tell a reader whether values survive the call -- the single
thing the other three exist to say. Read the body and pick one:
``project.project._refresh_metrics`` marked its stored snapshot fields to
recompute and flushed, so the state exists again afterwards, and it is
``_reset_metrics``.

**A reserved ORM verb on a method that opens a dialog costs a reader the whole
body** ``[review]``. ``project.phase.unlink_wizard`` created a wizard and returned
an action; nothing was deleted, and the name asserts two false things at once --
that the ORM operation runs, and that the wizard is its object. §2.4's opening
table already answers it: a view opener is ``action_view_*``, and ``action_open_*``
is the spelling for a wizard.

**Where the method name is also an XML id, one substitution is two** ``[review]``.
§2.4.14 says the key is not the method; the sharper case is the one where the two
are spelled the same. ``project.project.project_update_all_action`` returned the
``ir.actions.act_window`` whose id is ``project.project_update_all_action``, so a
whole-word substitution renames the record and every ``ref=`` pointing at it along
with the method. **Match the syntax rather than the name**: the whole attribute
value ``name="..."`` in view arch, and the call parenthesis in stored Python. The
method became ``action_view_project_updates`` and the record kept its id. The same
boundary is what protects a *longer* name that contains yours -- ``\yunlink_wizard\y``
leaves ``action_unlink_wizard`` alone, and a migration that gets this wrong is
found by reading the column, not by any test.

**Do not run a formatter over a directory to tidy up after a rename**
``[review]``. ``ruff format`` blocks on ``tests/`` only, so
``addons/`` and the sibling repositories are **not** format-clean at ``HEAD``, and
a directory-wide run rewrites files the rename never touched -- 35 of them in the
pass behind this entry, most of ``enterprise/helpdesk`` among them, in a workspace
several sessions are holding. ``ruff format $(git diff --name-only -- '*.py')``
reflows the lines the longer name actually broke and nothing else. Where such a
run has already happened, a file is safe to restore only once you have **shown**
its content is exactly ``ruff format`` applied to its ``HEAD`` content -- any edit
of somebody else's would have survived the formatting, and restoring would destroy
it.

**Neither is a whole-file write, for the same reason** ``[review]``. This section
was written, lost and written again inside one hour, because
``git checkout -- doc/coding_guidelines.rst`` and *"run the figure updater in a
worktree and copy the file back"* are both whole-file writes wearing the look of
housekeeping. In a shared checkout they silently discard every hunk that landed in
between, and this file has no index to protect it. Read a clean copy with
``git show HEAD:<path> >`` somewhere outside the checkout, edit by anchored hunk,
and re-read the anchor immediately before each write.

**Twelve shapes from one package the core gate read as clean** ``[review]``.
``odoo/db`` was swept by hand at ``d29958b31396`` while
``naming_core_vocabulary`` reported nothing there, and the names it renamed
fall into shapes a token gate cannot ask. Each is a finding with a rule behind
it; the ones an AST can settle are owed to that gate, the rest are review
questions with the instrument written down beside them.

* **A bare verb skips every body rule.** ``classify_definition`` returns
  ``None`` on a name with no remainder *before* the body-reading kinds run, so
  ``def _resolve(settings)`` that always produced one passed a gate whose own
  ``resolve-total`` rule names it. ``endpoints._resolve`` is
  ``_get_settings``; the rule binds the bare verb too.
* **An error built under a converter verb.** ``dsn._translate_connect_error``
  returned an exception it constructed -- ``InvalidCatalogName`` or
  ``InvalidAuthorizationSpecification`` -- or ``None`` for the caller to route,
  and never raised: §2.4.11's ``_resolve_connect_error``. Every return an
  exception is ``_prepare_*_error`` (§2.4.10); some returns ``None`` that the
  caller routes is ``_resolve_``. The AST can see a returned ``Call`` to a name
  ending ``Error`` / ``Exception`` / ``Violation``, which is the mechanical
  form of §2.4.10's *the larger half says no verb at all*.
* **Three verbs for writing a fact into held state.** ``mark_`` sets a flag on
  an object (``mark_locked``, ``mark_stale_cached_plan`` = ``setattr``),
  ``record_`` advances a counter (``stats.record_*``), and ``note_`` was used
  for either: ``reaper.note_activity(pool)`` set an attribute and is
  ``mark_active``; ``cursor._note_table_locked`` was one call to
  ``mark_locked`` and is ``_mark_table_locked``;
  ``bulk._note_binary_needs_exact_types`` was ``exc.add_note`` and is
  ``_add_binary_types_note`` -- §2.4.10's stand-in takes the callee's verb.
  ``note`` is a synonym and prints ``mark_`` / ``record_`` by the body.
* **A preposition-first predicate.** ``ddl._in_code_ranges`` returned
  ``any(...)``: a body that answers a question under a first token that is a
  preposition (``in``, ``within``, ``on``, ``at``, ``under``) is ``_is_`` /
  ``_has_`` -- ``_is_within_code_ranges``. A ``@property`` is exempt
  (``cursor.in_pipeline``, ``budget.in_use`` are nouns, §2.4.4).
* **``print_`` on a body that never prints.** ``metrics.print_log`` called a
  logger at ``DEBUG`` and no ``print()``; it is ``log_sql_stats``.
* **Two verbs for one classification in one package.** ``classify_statement``
  in ``ddl.py`` beside ``categorize_query`` / ``_categorize_write`` in
  ``metrics.py``: ``categorize`` is a synonym of ``classify`` and the pair is
  ``classify_query``, ``_classify_write_statement`` -- ``categorize`` /
  ``categorise`` are in the core gate's ``SYNONYMS`` now (``5b01cd9535ac``).
* **A chain renames the operation at each frame** -- §2.4.17's rule
  generalised. A body that is one call to a sibling with the same tail and a
  different verb (``_note_table_locked`` → ``mark_locked``) is the reason the
  reader has to open two frames to learn one fact. Candidate tier.
* **The frame that decides *why* owes ``invalidate_``.**
  ``cursor._note_stale_cached_plan(exc) -> bool`` cleared the prepared cache
  and the catalog facts and marked the exception, under a verb that said none
  of it; it is ``_invalidate_cached_plans_if_stale``.
* **A verbless partial producer.** ``replica._replica_cursor``, annotated
  ``Optional`` with the ``None`` routed by its caller, is
  ``_resolve_replica_cursor``. Candidate tier -- the annotation is the tell.
* **Three nouns for one thing in one file.** ``schema.get_foreign_keys``
  returned constraint *names* beside ``_get_fk_constraints`` and
  ``get_fk_constraints_batch`` returning rows; it is
  ``get_fk_constraint_names``. Naming standardisation is instrumental: the
  collision is the finding.
* **``normalize_`` whose output type differs from its input.**
  ``dsn._normalize_dsn_key`` took ``dict | str`` and returned a ``frozenset``:
  it built a key and normalised nothing, and is ``_get_dsn_key``.
* **One package, two spellings of a lossy typed conversion.**
  ``settings._optional_int`` beside ``endpoints._coerce_port`` were one
  operation; both are ``_coerce_optional_int`` (§2.4.5).

2.4.21 A prefix is a claim, and the claim is checkable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

§2.4.1 argues this for field hooks -- a reserved prefix asserts that a field
declaration somewhere names this method, and while the assertion is false the
spelling is unowned. §2.4.16 argues it for ``action_``, where the assertion is
that the client invokes the method by name. **Both are instances of one rule,
and it reaches every namespace a module invents**: a prefix that names a
protocol claims the protocol's dispatcher reaches this name, and the test is to
go and find the call. Where the prefix instead claims something about the
*return*, the test is the body. Neither test is expensive; what makes the claim
worth checking is that nothing else in the tree records it.

**A return annotation is the one thing that does record it, and it turns the
claim from a reading into a check** ``[review]``. A name says *what* comes back
in the only vocabulary a name has; ``-> Domain``, ``-> bool``, ``-> dict`` says
it in a vocabulary ``mypy`` and a reviewer read the same way. §2.4.1 already
rests a rule on exactly this -- the ``_get_*_domain`` exemption is read off the
annotation and never off the name, *because the name cannot say which ``domain``
it means and the annotation can*. **So annotate the return wherever the name
makes a type claim**: a ``_get_*_domain``, a predicate, a ``_prepare_*``, a
converter. That is where the annotation pays for itself, and it is not a call to
annotate the tree.

**The mechanism is real and almost unexercised, which is why it is written as an
instruction here rather than reported as a backlog** ``[review]``. Measured
2026-09-15 over the four repositories: **23.3 %** of production definitions carry
a return annotation, and the coverage is a repository fact rather than a tree
fact -- ``odoo`` 32.5 %, ``agromarin`` 24.8 %, ``enterprise`` **0.7 %**. Against
the claim families: of **8** surviving ``_get_*_domain`` definitions, **2** are
annotated and **none** returns an annotated ``Domain``, so §2.4.1's exemption
test would today decide nothing; of **1,706** predicates, **603** are annotated
and **595** of those say ``bool``, which is the family in the best shape and
still a third of it; of **2,242** ``_prepare_*``, **339** are annotated. **Of
the 952 definitions longer than 100 lines, 66 are annotated** -- the methods
whose contract is hardest to read from the body are the ones that state it least.

**And a type is a second axis for the duplicate search of §2.4.3** ``[review]``,
which is the argument for annotating that has nothing to do with type checking.
Two methods with the same object, the same return type and the same verb are
candidates to be one method, and the census groups them that way: **357** groups
of three or more share a verb and a full signature type. Naming alone cannot
raise that question, because the pair is already spelled correctly --
``_get_fields_select`` and ``_get_fields_pos_select`` both return ``dict`` and
sit in the same group. **Name, body and type are three different detectors; the
section has always argued the first, §2.4.3 now names the second, and this is
the third.**

**A protocol namespace is a claim about the caller** ``[review]``.
``point_of_sale`` declares its data-loading protocol on an ``AbstractModel``,
which is what §2.4.14 asks for -- and the declaration site did not stop the
namespace spreading past the protocol. *Frozen reading* (§1.4) at
``75ef0eec641``, an ad-hoc scanner over ``addons/``, ``enterprise/`` and
``agromarin/``: **8** names wear ``_load_pos_data_``, at **271** definitions.
The loader dispatches exactly **4** of them per model -- ``_search_read`` and
``_fields`` on ``self.env[model]``, ``_domain`` and ``_read`` through the first
of those -- at **246** definitions. The remaining **4**, at **25**, are one model's private helpers
wearing the protocol's spelling: ``_load_pos_data_country_ids`` was called only
by ``res.country``'s own ``_load_pos_data_domain``, and
``_load_pos_data_relations`` takes a model *name* and is reached as
``self.env["pos.session"]._load_pos_data_relations("pos.config", fields)`` --
a ``pos.session`` utility, not a member of the per-model protocol at all.

* **The cost is §2.4.1's collision, one level up.** A model implementing the
  protocol cannot tell from the names which of its ``_load_pos_data_*`` methods
  the loader will call and which are its own, and the dispatcher that settles it
  is in another file. Two are repaired here (``_get_referenced_country_ids``,
  ``_get_referenced_ids``); the other two are backlog, because their overrides
  are spread over three repositories -- which is the second cost, since a
  namespace that is not the protocol still recruits overriders as if it were.
* **A declaration site does not enforce the namespace, and no gate does either.**
  ``model_member_surface_check.py`` pins declared members, not the spelling of
  their neighbours. Read the dispatcher.

**``action_`` is the same claim, and §2.4.16 sizes only one of its directions**
``[review]``. That section counts ``action_*`` methods the XML names and says so;
the direction with the backlog in it is the other one. *Frozen reading* (§1.4) at
``75ef0eec641``, an ad-hoc scanner: **20** distinct methods are named by a
``<button ... type="object">`` in ``point_of_sale``'s views and wizards, and
**9** wore the prefix. Of the eleven that did not, eight are repaired here; the
three left are one decision, below.

**A JS call is not that claim, and reading §2.4.16's "a JS call" literally
inverts the rule** ``[review]``. Point of sale is a JS application talking to its
own models, so it is where that reading fails at scale: same frozen reading,
**14** distinct model methods are named from ``point_of_sale/static/src`` by
``orm.call`` / ``data.call``, and only **2** wear ``action_`` -- both of which
return an action the client executes. The other twelve are data RPCs
(``get_closing_control_data``, ``load_data_params``, ``get_existing_lots``) and
are right without the prefix. **The discriminator is not that the client names
the method, but that the client hands the return to its action service.** A
value the client fetches and reads is ``get_*`` however it is invoked.

* **The claim can also be false in the third direction -- ``action_`` on a
  method nobody invokes** ``[review]``, and it is the hardest of the three to
  settle. ``project.project.action_reset_metrics`` returns a bare ``True`` and
  is named by no XML, no JS and nothing but its own tests, which on the
  discriminator above is not an action. It is **not** repaired on that evidence,
  and its own module says why: ``project/migrations/1.19/post-migrate.py``
  rewrites four method names inside stored Python, so this model is known to be
  reached from a database column §2.4.19 warns no grep can see. **Where the
  claim is about a caller and the caller may be in a database, "nothing greps
  it" is not the answer** -- the reading needed is the ``noupdate`` test in
  §2.4.19, not a wider grep.
* **A ``_cb`` tail is that claim written backwards** ``[review]``. It records
  that something calls back -- which §2.4.9 already objects to as a role rather
  than an operation -- while saying nothing about *who*, which is the half that
  would have been worth writing. Both of this module's were client-named
  buttons: ``open_existing_session_cb`` is ``action_view_current_session`` and
  ``open_frontend_cb`` is ``action_open_frontend``.

**A predicate prefix is a claim about the return, and the same test applies to
it** ``[review]``. ``pos.config._is_journal_exist(journal_code, name,
company_id)`` searched for a journal, **created one when it found none**, and
returned an ``id``; ``_is_pos_pm_exist`` was the same method for payment
methods. Three prefixes' worth of claim, all false: ``_is_`` promises a ``bool``
answering a question about the subject (§2.4.8), ``exists`` is reserved for
``recordset.exists()`` and schema introspection (§2.4.3), and a predicate does
not write. **Where a name breaks three rules at once, do not repair them one at
a time**: ask which row's discriminator the *body* satisfies and rename once.
§2.4.11's canonical answers all three in one move -- ``_get_or_create_journal_id``
and ``_get_or_create_payment_method_id``, with §2.4.15's tail rule supplying the
``_id`` that says what comes back.

* **The worst case is the one where the prefix is the whole name.**
  ``pos.make.payment.check()`` takes the payment, writes it to the order and
  returns an action, behind a button reading *Make Payment*. It is not a
  ``check_*`` whose object is wrong (§2.4.20's ``check_features_enabled`` is
  that); it has no object at all, so §2.4.4's verb-object rule, the Validation
  row and §2.4.16's binding all fail on the same four letters, and it was 45
  call sites deep across three repositories. **A one-word public method name is
  worth reading on sight**: there is nowhere in it for a discriminator to be,
  so it is either a domain operation on the receiver (§2.4.6) or a name nobody
  ever finished. It is ``action_make_payment``.

**The caller's variable is evidence, in the one place the body cannot be**
``[review]``. §2.4.4 reads the variable a method returns, in its own body. On an
**extension point** that evidence is missing by construction -- §2.4.11 already
warns that such a body is the least informative in the tree -- and the variable
worth reading is at the call site, written by the consumer.
``mixin.pos.load._unrelevant_records(config)`` returned ``.ids`` under a name
promising records, and its one caller in ``pos.session`` had written
``inactive_ids = set(existing_records._unrelevant_records(...))``: the name it
was owed was ``_get_inactive_ids``, spelled out three files away by the only
code that had to know what it got. **Read the call sites of an override point
before its body**, and prefer what the consumer called the value.

**Where the name and the body disagree completely, the rename is a product
question and the pass stops** ``[review]``. ``pos.config.close_ui`` is
``return self.open_ui()``, and ``res.config.settings.pos_close_ui`` is
``return self.pos_open_ui()``; each is named by a button reading *Click here to
close the session*, and each opens the point-of-sale UI, which is where a
session is then closed. No spelling repairs that. Either the alias exists so a
downstream module can override one button without the other -- ``pos_self_order``
does override ``close_ui`` -- and it is owed a name saying which button it
serves, or it is dead and the repair is deletion. **Both are left as found on
purpose**, together with ``open_ui``, and this paragraph is the record that they
were read and not missed. A naming pass that guesses here writes a name that is
merely differently wrong.

2.4.22 Reshaping the receiver is not producing a value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**A method whose whole body is one ORM shaping call hands back the receiver
reshaped, and the vocabulary above has no row for it** ``[review]``. Every verb
in §2.4.3 names a method that *produces* something -- reads it, builds it, writes
it, answers about it. ``self.filtered(...)``, ``self.sorted(...)``,
``self.grouped(...)`` and the ``with_*`` family produce nothing: the rows are
already in ``self``, or they are the same rows under a different environment. A
caller told ``_get_`` has to open the body to learn that, and what it learns
there is the thing most worth knowing -- that the return is a **subset of what it
passed in**, or **the same records with different privileges**.

*Frozen reading* (§1.4) at ``45275737cf4``, an ad-hoc scanner, not re-derivable.
**181** model methods return nothing but one such call; **11** are spelled for
the operation they perform.

.. list-table::
   :header-rows: 1
   :widths: 14 12 12 62

   * - Shape
     - Canonical
     - Here
     - What the name has to carry
   * - Re-envelope
     - ``_with_*``
     - 2 of 25
     - the same rows, a different environment -- context, company, user,
       ``sudo``. The **rows are not the subject**; the envelope is
   * - Narrow
     - ``_filtered_*``
     - 6 of 140
     - a subset of the receiver, never a row the caller did not hand in
   * - Order
     - ``_sorted_*``
     - 3 of 15
     - the same rows in a stated order; the order **is** the return value
   * - Group
     - ``_grouped_*``
     - 0 of 1
     - a mapping whose values partition the receiver

**The past participle is the ORM's own spelling, not a missing verb**
``[review]``. §2.4.4 objects to a name with no verb, and ``_filtered_expired``
can be misread as one. It is not: ``filtered``, ``sorted`` and ``grouped`` are
the names the framework gives these operations, and a method wrapping one is a
§2.4.10 stand-in -- it takes the callee's spelling and gains only the
qualifier. ``_filter_effective_pickings`` is the version that got this wrong in
the other direction, inventing ``_filter_`` for an operation the ORM already
spells.

**The re-envelope shape is the one that misleads hardest** ``[review]``, because
its natural wrong name states the wrong *return type* rather than a merely vague
one. ``stock.quant._set_view_context`` and ``_blocked_gather_context`` both
returned ``self.with_context(...)`` while promising a context; a caller
reasonably wrote ``context = record._set_view_context()`` and got a recordset.
Both are ``_with_*``. The tell is the assignment at the call site: a
re-enveloper is nearly always assigned back over the receiver
(``self = self._with_view_context()``), which is a shape no getter ever has.

* **A ``_check_`` that returns a subset is in this section, not §2.4.8.**
  ``_check_line_unlink`` returns ``self.filtered(...)``; it neither raises nor
  answers, so the Validation row and the Predicate row both miss it and the
  reserved prefix is spent on a narrowing.
* **``_without_*`` is the complement spelled as a preposition**, at **7**
  definitions under **3** names, and it spans two of the four shapes at once --
  ``_without_no_variant_attributes`` narrows, ``_without_putaway_scan``
  re-envelopes. It reads as a filter and sometimes is one, but it names what is
  **absent** from the return, which is the one thing a recordset cannot show
  you. Say what comes back.
* **Do not extend this to a method that also does something else.** The rule is
  for a body that is one shaping call. A method that searches, then filters,
  returns rows the caller never held, and is a read.

**A producer prefix on a body that is one shaping call is gated** ``[gate
naming]``. ``reshaped_receiver`` in ``naming_vocabulary.py`` reports a
``_get_``, ``_check_``, ``_set_``, ``_prepare_`` or ``_resolve_`` whose body --
docstring aside -- is a single ``return self.filtered(...)``,
``self.filtered_domain(...)``, ``self.sorted(...)``, ``self.grouped(...)``,
``self.sudo()`` or ``self.with_*(...)``, and prints the row's spelling. It is
exactly the frozen reading above made repeatable, and it is narrower than the
reading on purpose: the receiver has to be ``self`` (``lines.filtered(...)`` on
a parameter is a read of something the caller handed in, and §2.4.22 has no
row for it), and the body has to be that one statement, so the bullet above is
enforced rather than merely stated. *Frozen reading* (§1.4) at the commit that
landed it: **11** in ``addons/`` -- ten ``_get_`` and the ``_check_line_unlink``
the bullet above already named -- **5** in ``enterprise``, **3** in
``agromarin``. ``phone.number._primary(*types)``, which narrows to the first
number of the given types, is the same shape without a prefix to report on;
it is ``_filtered_primary`` by this section and is left as it is, because it
is reached from mail templates in six modules and from shipped translation
catalogues, and a rename there is a §2.4.14 batch with a stored-data
migration, not a tidy-up.

2.5 Docstrings and comments
---------------------------

Mandatory on models and on non-trivial methods ``[review]``. Simple accessors may
omit them.

**No linter enforces presence** ``[review]``. ``ruff``'s ``D`` rules are not
selected and the ``ruff_docstring`` ratchet is retired. **Accuracy is still
mechanical**: ``DOC`` (pydoclint) remains selected and fires only on docstrings
that *exist* -- an extraneous ``:param:``, a documented exception that cannot be
raised -- and where a docstring documents parameters, its fields must agree with
the signature ``[test_lint test_docstring]``. Nothing obliges you to write one;
writing a wrong one still fails.

**Two bodies of docstrings are load-bearing and must not be removed.**
``odoo/cli/`` docstrings are the CLI's user-facing help text, rendered by
``help.py`` and fed to argparse by ``command.py``; the since-deleted
``upgrade_code.py`` string-replaced one and raised ``AttributeError`` the moment
it became ``None``. A handful more are machine-checked contracts read by
``tests/service/`` (``http/tests/test_openapi.py``; ``orm/__init__.py`` and
``orm/models/mixins/_metadata.py`` were read by ``tooling/architecture/``,
gone since 2026-09-11). Deleting one of those breaks a test, not a style gate.

``service/__init__.py`` and ``service/db/`` were on that list and are **no longer
load-bearing**. Their reader was ``tests/service/test_module_layout.py``, which
parsed a "Module layout:" block out of ``odoo.service.__doc__`` — and the
prose-and-docstring strip emptied it, so the gate passed while detecting nothing,
failing for exactly the reason it existed to prevent. It now reads
``doc/architecture/module.md``: a document rather than a docstring, which a
strip cannot empty. Verified: nothing under ``tests/`` reads either module's
``__doc__``, and ``service/db/listing.py`` sat at zero
documented definitions with ``tests/service`` fully green.

The general rule above still applies to both — a docstring there is optional and
judged on whether it earns its place, not protected by a gate.

Use Sphinx fields:

.. code-block:: python

   class SaleOrder(models.Model):
       """Sales order management with multi-currency support."""

       def _prepare_invoice_vals(self, order_line):
           """Prepare values for invoice creation.

           :param recordset order_line: lines to invoice
           :return: values accepted by ``account.move.create``
           :rtype: dict
           """

* One line for a model docstring: what the entity *is*.
* Field-by-field listings belong in each field's ``help=``, not the class
  docstring.
* ``"""triple double quotes"""``, never ``'''single'''``.
* **Be correct.** Verify every claim against the code; delete stale references. A
  docstring that contradicts the code is worse than none -- update it in the same
  edit that changes a signature, a return type or a behaviour.
* **Be direct.** Cut *Basically*, *Essentially*, *Note that*, *This method
  simply*. Use the imperative: "Return…", "Raise…", "Compute…".
* **Do not restate the obvious.** A docstring echoing the method name, or
  retyping the signature, is noise.
* **Comments explain why, not what.** A comment narrating the next line has
  earned its deletion.

**The protection above covers what a machine reads; nothing covers what only a
person reads** ``[review]``, and that is by far the larger set. The
load-bearing-docstring rule names the bodies a gate or a test parses, and the
``service/__init__.py`` case beside it is a condensing pass emptying one -- where
at least a gate went vacuous and could in principle be caught. **A comment is
read by nothing, so its deletion moves no figure, breaks no test and leaves no
evidence that it existed.** The only detector is a reader who already knew.

    the recorded case   a strip emptied a docstring a **gate** read
                        -> the gate passed while detecting nothing
    the wider case      a strip deleted a comment only a **person** read
                        -> nothing detected anything, and nothing could

The evidence is ``orm/validation.py``'s ``regex_pg_name``: four tokens of regex
whose lowercase-only form is a deliberate divergence from upstream. The comment
recording why -- PostgreSQL folds unquoted identifiers, so ``MyTable`` and
``mytable`` collide -- **and the scope of the survey that made the narrowing
safe** was removed by a commit condensing inline docs. The reasoning survived
only inside that commit's diff, and a later reader met a narrowed regex, a
``ValidationError`` worded for tables, and four failing tests in another
repository with no route to any of it.

**So: deleting an existing comment is a separate decision from shortening one.**
Leave it unless it is now false. A pass that condenses prose reads each comment
against the *why* test first and shortens **around** the reason rather than
through it; where the reason is genuinely stale, removing it is a decision that
says so. This rule has lived in the workspace ``CLAUDE.md`` and not here, which
is the split the change protocol exists to prevent -- the canonical is this
document, and a rule that only the harness file states is a rule the guide does
not have.

2.6 ORM
-------

**Always ``super()``** in ``create``, ``write``, ``unlink``, ``copy_data``,
``default_get`` and ``_compute_display_name`` ``[review]``. Prefer overriding
``copy_data`` over ``copy`` -- it is the values hook ``copy`` is built on.

**Override ``create`` in batch form** ``[review]``:

.. code-block:: python

   @api.model_create_multi
   def create(self, vals_list):
       for vals in vals_list:
           ...
       return super().create(vals_list)

**Every model declares ``_name`` and ``_description``** ``[review]``. Set
``_order`` when insertion order is wrong. For the record label set ``_rec_name``,
or override ``_compute_display_name`` calling ``super()``; ``name_get`` no longer
exists.

**Deletion constraints use ``@api.ondelete``** ``[test_lint E8506]``. A ``raise``
inside an ``unlink()`` override fails the checker -- the override runs at
uninstall too, and blocks it.

.. code-block:: python

   @api.ondelete(at_uninstall=False)
   def _unlink_except_confirmed(self):
       if any(r.state != "draft" for r in self):
           raise UserError(self.env._("Cannot delete a confirmed order."))

**The framework owns transactions.** Do not call ``self.env.cr.commit()`` or
``rollback()`` from business code. Only the framework, the cron runner and code
holding its own cursor (``self.env.registry.cursor()``) may commit.

**Assign fields directly in computes** (``self.field = value``); ``write()`` in a
compute recurses.

**``check_singleton()``** at the top of any method that assumes a single record.

**Context is a frozen dict** -- propagate with ``with_context``. For company
scoping use ``with_company``:

.. code-block:: python

   order.with_context(tracking_disable=True).action_confirm()
   order.with_company(company).action_confirm()   # not with_context(force_company=...)

**``force_company`` fails silently, so grep for it rather than waiting for an
error.** ``with_context(force_company=...)`` emits a ``DeprecationWarning`` and
otherwise does nothing: no exception, the key stays in the context, nothing reads
it, and surviving call sites run against the *wrong company*.

**Prefer recordset operations** -- ``filtered``, ``mapped``, ``sorted`` -- over
manual loops, and ``odoo.tools.groupby`` over ``itertools.groupby``: it handles
recordsets and needs no pre-sorting.

**Think extendable.** Avoid hard-coded values that should be configuration. Split
methods so another module can override one piece without copying the rest.

**Deprecate explicitly**:

.. code-block:: python

   @api.deprecated("Since 19.0, use _prepare_invoice_vals instead")
   def _prepare_invoice(self):
       return self._prepare_invoice_vals()

ORM performance -- counts, aggregation, batching, N+1, indexing, locking,
``ormcache``, cron batching -- is **§11**, their single source.

2.7 Error handling
------------------

.. list-table::
   :header-rows: 1

   * - Exception
     - Use for
   * - ``UserError``
     - Business-logic violations the user can act on
   * - ``ValidationError``
     - Constraint failures inside ``@api.constrains``
   * - ``AccessError``
     - Permission and security violations (HTTP 403)
   * - ``RedirectWarning``
     - Errors the user resolves by navigating somewhere
   * - ``MissingError``
     - The record is gone or inaccessible
   * - ``ValueError``
     - Invalid arguments to internal methods -- never user-facing

**User-facing exceptions take a translated message, not a raw literal**
``[test_lint E8505]``. ``UserError``, ``ValidationError``, ``AccessError``,
``AccessDenied`` and ``MissingError`` all require the first argument to go through
``self.env._()`` (§8.1):

.. code-block:: python

   raise UserError(self.env._("Order %s cannot be confirmed.", order.name))
   raise RedirectWarning(
       self.env._("Please configure a default warehouse."),
       action_id,
       self.env._("Go to Settings"),
   )

**Never leak internals**:

.. code-block:: python

   # Wrong — exposes stack internals, SQL fragments, paths
   except Exception as e:
       raise UserError(str(e))

   # Right — generic message to the user, full traceback in the log
   except Exception:
       _logger.error("Payment processing failed", exc_info=True)
       raise UserError(self.env._("Payment could not be processed. Contact support."))

**Fail closed.** Wrap each iteration in a savepoint so a failure rolls back or
transitions to an explicit error state. In financial or state-mutation code,
log-and-continue is a violation:

.. code-block:: python

   for order in orders:
       try:
           with self.env.cr.savepoint():
               order._process_payment()
               order.action_confirm()
       except UserError:
           order.state = "error"
           _logger.error("Failed to process order %s", order.name, exc_info=True)

``except Exception`` is ``[review]`` -- ``BLE001`` is disabled in ``ruff.toml``
because Odoo legitimately catches ``Exception`` around external and ORM calls. Use
it for catch-log-reraise and for integration adapters, not as a default.

**Chain exceptions**: ``raise X from Y`` (or ``from None``) inside ``except``
``[ruff B904]``.

2.8 Controllers
---------------

.. code-block:: python

   from odoo import http
   from odoo.http import request


   class SaleController(http.Controller):
       @http.route("/shop/cart", type="http", auth="public", methods=["GET"], website=True)
       def cart(self):
           order = request.website.sale_get_order()
           return request.render("website_sale.cart", {"order": order})

       @http.route("/api/orders", type="jsonrpc", auth="bearer", methods=["POST"])
       def create_order(self, **kwargs):
           order = request.env["sale.order"].create(kwargs)
           return {"id": order.id}

.. list-table::
   :header-rows: 1

   * - Parameter
     - Values
   * - ``type``
     - ``"http"`` (HTML/binary) or ``"jsonrpc"``
   * - ``auth``
     - ``"user"`` (default), ``"public"``, ``"bearer"`` (API token), ``"none"``
   * - ``methods``
     - ``["GET"]``, ``["POST"]``, …
   * - ``csrf``
     - default ``True`` for ``http``, ``False`` for ``jsonrpc``

An overriding controller re-declares the route with ``@route()`` but **must not
restate attributes it does not change** ``[test_lint test_routes]``: repeating
``type=`` and ``auth=`` at their inherited values hides what the override
modifies. Controller security is §10.6.

2.9 Patterns
------------

2.9.1 ``Domain``
~~~~~~~~~~~~~~~~

.. code-block:: python

   from odoo.fields import Domain

   domain = Domain("state", "=", "draft")
   combined = Domain("state", "=", "draft") & Domain("partner_id", "!=", False)
   either = Domain("type", "=", "out_invoice") | Domain("type", "=", "out_refund")
   negated = ~Domain("active", "=", False)

   Domain.AND([d1, d2, d3])
   Domain.OR([d1, d2])
   Domain.TRUE      # matches everything
   Domain.FALSE     # matches nothing

Use ``Domain`` for anything built programmatically. The list-of-tuples form stays
valid for static domains in XML and data files.

2.9.2 Recordset safety
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   records = records.exists()        # drop rows deleted by another transaction

   record = self.env["sale.order"].browse(record_id).exists()
   if not record:
       raise MissingError(self.env._("Record %s has been deleted.", record_id))

2.9.3 Context keys
~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Key
     - Effect
   * - ``active_test``
     - ``False`` includes archived records in searches
   * - ``lang``
     - force a language
   * - ``tz``
     - force a timezone for display
   * - ``default_<field>``
     - default value for new records
   * - ``active_ids`` / ``active_model``
     - source records for wizards and server actions
   * - ``tracking_disable``
     - suppress mail tracking on ``write()`` -- for bulk imports

A field may carry its own context for relational access:

.. code-block:: python

   child_ids = fields.One2many("res.partner", "parent_id", context={"active_test": False})

2.9.4 Monetary fields
~~~~~~~~~~~~~~~~~~~~~

``fields.Monetary`` needs a companion currency. A missing one trips an ``assert``
in ``Monetary.setup_nonrelated`` / ``setup_related``, so it fails when the registry
is built -- at module load, not on first use -- and not at all under ``python -O``
(§10.3):

.. code-block:: python

   currency_id = fields.Many2one("res.currency", required=True)
   amount_total = fields.Monetary()                              # picks currency_id

   base_currency_id = fields.Many2one("res.currency")
   amount_in_base = fields.Monetary(currency_field="base_currency_id")

2.9.5 String formatting
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Context
     - Use
     - Never
   * - General code, exception messages
     - f-strings
     - --
   * - Translations
     - ``%s`` / ``%(name)s`` args to ``self.env._()``
     - f-strings -- extraction silently breaks
   * - Logging
     - ``%s`` args to the logger
     - f-strings ``[ruff G004]``
   * - SQL parameters
     - ``%s`` placeholders
     - f-strings -- injection ``[test_lint E8501]``
   * - HTML in errors
     - ``%``-style or ``.format()`` inside ``Markup()``
     - f-strings -- XSS

2.9.6 Datetime
~~~~~~~~~~~~~~

``datetime.utcnow()`` is banned twice over ``[ruff DTZ003]`` and by ``banned-api``;
``utcfromtimestamp`` likewise ``[ruff DTZ004]``. Most other ``DTZ`` rules are off,
because the ORM stores naive UTC by design.

.. code-block:: python

   from datetime import UTC, datetime

   now_aware = datetime.now(UTC)                          # external APIs
   now_naive = datetime.now(UTC).replace(tzinfo=None)     # ORM Datetime fields

Comparing an aware ``datetime.now(UTC)`` with a naive ORM value raises
``TypeError``. Odoo pins the process timezone to UTC at startup, so inside a
running server the OS-local zone *is* UTC -- a discrepancy reproduced outside Odoo
is usually an artefact of the harness.

2.9.7 ``Command`` for x2many writes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``odoo.fields.Command`` ``[review]``; the raw magic tuples are unreadable.

.. code-block:: python

   from odoo.fields import Command

   order.write({
       "line_ids": [
           Command.create({"product_id": p.id, "qty": 1}),   # was (0, 0, {...})
           Command.link(existing_line.id),                    # was (4, id)
           Command.set(new_line_ids),                         # was (6, 0, [...])
           Command.clear(),                                   # was (5, 0, 0)
       ],
   })

2.9.8 SQL constraints
~~~~~~~~~~~~~~~~~~~~~

Declare them with ``models.Constraint`` in the ``# CONSTRAINTS`` section
``[review]``. The legacy ``_sql_constraints = [...]`` list is deprecated.

.. code-block:: python

   # CONSTRAINTS
   _amount_positive = models.Constraint(
       "CHECK(amount >= 0)",
       "The amount must be positive.",
   )
   _code_unique = models.Constraint(
       "UNIQUE(code, company_id)",
       "Code must be unique per company.",
   )

**The attribute names the columns, and nothing checks that it does** ``[review]``.
``TableObject.__set_name__`` takes the attribute name verbatim and ``full_name``
builds the PostgreSQL identifier as ``{table}_{attr}``, so the attribute is the
constraint's name in the database, in ``ir.model.constraint`` and in every error a
user sees. No linter reads it -- ``test_translated_unique`` checks the *column* --
so a constraint can name a column the table lost four major versions ago
(``ir.model``'s ``_obj_name_uniq``, declared ``UNIQUE (model)``). Name the columns
the definition names, in the order it names them, and keep the predicate in the
tail -- the tree spells that tail ``_uniq`` **102** times against ``_unique``'s
**53**, so prefer ``_uniq`` for a new one and do not sweep the others for it.

**A constraint rename is carried by module-data cleanup, not by a migration**
``[review]``. ``_reflect_constraints`` registers each constraint as module data
under ``{module}.constraint_{conname}``; on the next upgrade the old xmlid is
absent from ``loaded_xmlids``, ``ir.model.data._process_end`` unlinks the orphan,
and ``IrModelConstraint.unlink`` drops the constraint it names. Do not write a
migration for one.

**What the rename does break is the translations, and that binding is invisible**
``[review]``. ``message`` is a translated field on a *record*, so its translations
are keyed by the record's external id -- the
``#: model:ir.model.constraint,message:base.constraint_<conname>`` reference in
each ``i18n/<lang>.po``. The upgrade deletes the old record and creates a new one,
so a rename that does not sweep those references leaves every translation matching
nothing, in silence, and the message reverts to English. ``_obj_name_uniq`` was
named in **64** of ``base``'s catalogues, the ``.pot`` template among them -- miss
that one and the next export puts the stale reference back.

**Never declare UNIQUE over a translated column** ``[test_lint E8512]``. A ``translate=True`` field is stored as
``jsonb``, so the constraint compares whole translation *documents* rather than
values: two rows stop colliding the moment one carries a language the other does
not. That is the next create, not a later translation step, because Odoo writes
the active language alongside the source term -- so the rule enforces nothing,
silently, and only in databases with a second language.

Use ``name_uniq_index()`` from ``odoo/addons/base/models/mixin_catalog.py``, which
indexes the source term. It is a ``models.UniqueIndex`` rather than a
``Constraint`` because the comparison is an expression, which PostgreSQL does not
allow in a UNIQUE constraint:

.. code-block:: python

   # CONSTRAINTS
   _name_src_uniq = name_uniq_index(
       "company_id",
       message="A template with this name already exists for this company.",
   )

When **converting an existing** ``UNIQUE(name, ...)``, pass ``nulls_distinct=True``
so only the comparison changes. The helper otherwise defaults to
``NULLS NOT DISTINCT``, right for a catalog adopting the rule for the first time
but tighter than the old constraint: a plain UNIQUE never fired for two rows
sharing a NULL scope column, and code relies on that (``res.groups`` holds several
same-named groups with no privilege).

2.9.9 Onchange
~~~~~~~~~~~~~~

``@api.onchange`` takes plain field names -- dotted paths are silently ignored.
The method runs on a pseudo-record that may not exist in the database, so calling
any CRUD method on it is undefined behaviour; assign fields or call ``update()``.

**Returning a domain from an onchange is forbidden**
``[test_lint test_onchange_domains]``. Dynamic domains belong on the field
(``domain=``) or in the view, where they survive the round trip. An onchange may
still return a ``warning`` dict.

A One2many or Many2many field cannot modify itself through an onchange -- a
webclient limitation, not a fork one.

2.9.10 Multi-company
~~~~~~~~~~~~~~~~~~~~

Multi-company correctness is a fork-wide requirement ``[review]``:

* Relational fields that must stay inside the record's company carry
  ``check_company=True`` (the model needs a ``company_id``).
* Per-company scalar configuration uses ``company_dependent=True``.
* Read the active company as ``self.env.company``; scope work with
  ``with_company(company)``. Never guess or hard-code a ``company_id``.
* Company record rules use ``[("company_id", "in", company_ids + [False])]`` so
  company-less shared records stay visible (§10.8).

.. code-block:: python

   company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
   warehouse_id = fields.Many2one("stock.warehouse", check_company=True)
   default_journal_id = fields.Many2one("account.journal", company_dependent=True)

2.9.11 Type hints
~~~~~~~~~~~~~~~~~

Optional but encouraged for public API, framework code and non-obvious return
types ``[review]``. ``ANN`` is linted only in ``odoo/libs/`` and
``odoo/orm/components/``. Python 3.14's PEP 649 deferred annotations mean forward
references work unquoted.

**Modern generics only** ``[ruff banned-api]``: ``list[X]``, ``dict[K, V]``,
``tuple[X, ...]``, ``X | None``. ``typing.Optional``/``List``/``Dict``/``Tuple``/
``Set``/``Union`` are banned.

.. code-block:: python

   from typing import TYPE_CHECKING, override

   if TYPE_CHECKING:
       from .res_users import ResUsers


   class ResPartner(models.Model):
       _name = "res.partner"

       user_ids: ResUsers = fields.One2many("res.users", "partner_id")

       @override
       def create(self, vals_list):
           ...
           return super().create(vals_list)

Apply ``@typing.override`` to overridden parent methods. It is not linted, but it
pairs with the signature gate in §2.4.15: together they turn a renamed or
re-signed parent from a silent behaviour change into an error.

2.9.12 Float and currency comparison
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Never compare floats or ``Monetary`` values directly.** Use the ORM helpers,
passing ``precision_rounding=<currency>.rounding`` or ``precision_digits=<n>``.
Do not invent epsilons.

.. code-block:: python

   from odoo.tools import float_compare, float_is_zero, float_round

   rounding = order.currency_id.rounding
   if float_is_zero(line.price_subtotal, precision_rounding=rounding):
       ...
   if float_compare(paid, total, precision_rounding=rounding) >= 0:    # paid >= total
       order.state = "paid"
   amount = float_round(raw_amount, precision_rounding=rounding)

``[ruff RUF069]`` covers ``==`` and ``!=`` **only**, and only where it can infer
that both operands are floats. Ordering comparisons and anything behind a
recordset attribute are ``[review]``. The linter is a backstop, not coverage.

2.9.13 Logging
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Level
     - Use for
   * - ``debug``
     - development diagnostics; off in production
   * - ``info``
     - normal business events (import finished, cron ran)
   * - ``warning``
     - recoverable issues, deprecated usage, fallback paths
   * - ``error``
     - unhandled exceptions and data corruption -- with ``exc_info=True``

Pass arguments lazily; f-strings in a logging call are linted ``[ruff G004]``, and
eagerly stringifying an argument is too ``[ruff RUF065]``.

For cross-model flows (invoicing, EDI, payments) put a correlation identifier in
every line so one business transaction can be traced end to end:

.. code-block:: python

   _logger.info("[order:%s] Starting invoice creation", order.name)
   _logger.info("[order:%s] PAC stamping completed, UUID: %s", order.name, uuid)

2.9.14 Background jobs (``ir.job``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For deferred one-off work use the framework job queue -- not ad-hoc threads, not
``cr.commit()`` loops, not the legacy OCA ``queue_job``. Crons remain the tool for
*recurring* work; ``ir.job`` is for "run this later, in the background, with
retries" ``[review]``.

.. code-block:: python

   class StockPicking(models.Model):
       _inherit = "stock.picking"

       @api.job(channel="wms", max_retries=3)
       def _sync_to_wms(self, batch_size=100):
           ...

   # enqueued in the current transaction, executed after commit
   picking.delayed(priority=5, eta=60)._sync_to_wms(batch_size=50)

* Job methods are **private**; the decorator rejects a public name, and the worker
  refuses to run anything undecorated -- a hand-crafted ``ir_job`` row cannot call
  arbitrary code.
* Arguments must be **JSON-serialisable**. Pass ids, not recordsets or datetimes;
  the records the job targets ride on ``delayed()``'s own recordset.
* Write bodies **idempotent or transaction-safe**. Completion is atomic with the
  job's writes, so partial effects never survive a crash -- external side effects
  (HTTP calls, mail) need their own guards.
* Transient failures raise ``RetryableJobError(seconds=...)``; any other exception
  also consumes one of ``max_retries`` before the job is marked failed. Both roll
  the job's transaction back.
* Concurrency is bounded per **channel**. A channel absent from ``ir.job.channel``
  has an implicit capacity of 1 -- give heavy integrations their own channel
  instead of tuning priorities.
* Chain with ``delayed(after=job)``, fan in by passing a union, collapse bursts
  with ``identity_key``. A deferral does **not** release dependents.
* Defaults: ``channel="root"``, ``priority=10``, ``max_retries=5``,
  ``max_defers=100``.
* Ops surface: Settings → Technical → Automation → Background Jobs. Smoke-test a
  deployment with ``env["ir.job"].delayed()._job_ping()``.

**Not finished is not failed** ``[review]``. Where the body cannot complete
because something outside it is not ready, call
``self.env["ir.job"]._defer(seconds, reason=...)`` and return normally: the job's
writes are kept and committed, ``retry`` is untouched, nothing is recorded in
``exc_*``, and the job keeps its ``identity_key`` so a caller cannot queue a
duplicate while it waits. Deferrals have their own budget, ``max_defers``.

.. code-block:: python

   @api.job(channel="sat", max_retries=3, max_defers=24)
   def _poll_remote_package(self):
       self._record_progress()          # kept, whatever happens next
       if not self._package_ready():
           self.env["ir.job"]._defer(600, reason="still preparing")

Do not reach for ``RetryableJobError`` here: it is an exception, so the progress
just recorded is rolled back, and it spends a retry per attempt. Re-enqueueing a
fresh job from inside the body does not work either -- a running job is in a
queued state and still holds its ``identity_key``, so the enqueue is silently
dropped.

2.10 Lazy imports
-----------------

**Imports go at module level unless there is a documented reason.** Imports inside
functions hide dependencies, duplicate across methods and defeat module-graph
analysis. ``PLC0415`` is globally suppressed because Odoo's architecture genuinely
requires some lazy imports -- which makes this ``[review]`` and makes the
explanatory comment mandatory.

Acceptable reasons:

#. A **circular dependency** that cannot be restructured away:

   .. code-block:: python

      def json_default(obj):
          from odoo import fields  # circular: tools -> fields
          ...

#. An **optional external dependency**, guarded by ``try`` / ``except ImportError``.
#. **CLI startup cost** -- keeping ``--help`` fast.
#. **``import odoo.addons``**, whose ``__path__`` is populated at runtime.
#. **Addon model imports from framework code**, not registered at framework import
   time.

"Just in case" is not a reason. If the same import appears in two functions of one
file, promote it.

----

3. XML
======

3.1 Format
----------

Formatting and ordering are **owned by fixers** -- do not hand-align
``[test_lint test_pretty_xml, test_xml_records]``
``[fixer _pretty_xml, _sort_xml_records]``. Run the sorter first and the formatter
last: the formatter preserves order, the sorter does not preserve formatting.

The conventions they enforce:

* The ``<?xml version="1.0" encoding="utf-8"?>`` declaration on line 1; 4-space
  indentation; root element ``<odoo>``, not ``<data>``.
* Double-quoted attribute values; empty elements self-close.
* Attribute order: ``id`` then ``model`` on records; ``name`` first on fields;
  ``menuitem``, ``template``, ``delete`` and ``function`` each have their own
  order (``ATTRIB_ORDER`` in ``odoo/addons/test_lint/tests/_sort_xml_records.py``).
* Attribute order inside a view arch (``ARCH_ATTRIB_ORDER``, same file, every
  view-semantic element, HTML left alone): what it is (``name``/``for``/``expr``,
  ``position``, ``special``, ``type``) → what it says (``string``, ``placeholder``,
  ``help``, ``confirm``) → how it renders (``widget``, ``icon``, ``col``,
  ``nolabel``, ``optional`` ...) → what data it takes (``domain``, ``context``,
  ``options``, ``default_order``, ``editable`` ...) → when it applies (``groups``,
  ``invisible``, ``column_invisible``, ``readonly``, ``required``) → ``class``,
  ``style`` → anything else alphabetically. The conditions a reviewer reads for
  bugs sit together, just before the styling.
* Field order inside a record: ``FIELD_ORDER`` in the same file is the canon,
  one list per technical model (``ir.ui.view``, the ``ir.actions.*``,
  ``ir.rule``, ``ir.cron``, ``res.groups``, ``mail.template``, ...): identity
  first, the large ``arch`` / ``help`` / ``body_html`` last, fields outside the
  list alphabetical after it. Every name in it is a field of its model
  ``[test_lint test_fixers]``; a rename must carry the canon with it. Business
  models (``res.partner``, ``product.product``, the ``account.*`` data) have no
  canon and keep their written order.
* One blank line between top-level records, and after ``<odoo>`` / before
  ``</odoo>``.
* 88 columns; a tag exceeding it wraps one attribute per line. A single attribute
  longer than 88 -- a large ``domain`` or ``context`` -- stays on its own line.
* ``domain``, ``context`` and ``options`` values go on **one line**. XML
  normalises newlines inside an attribute value to spaces, so a multi-line form
  is purely cosmetic and cannot survive the formatter.

The static rules over the same files -- ``[test_lint test_xml_lint]``, the
vocabulary in ``odoo/addons/test_lint/tests/_xml_rules.py``, one ``lint_xml_*``
ratchet each, zero unless ``floors.json`` says otherwise:

* The root element is ``<odoo>`` (``data-root``); every data file is listed
  under ``data`` or ``demo`` in the manifest, or loaded by path from the
  module's Python (``orphan-data-file``) -- an unlisted file's records never
  exist, and an ``env.ref(..., raise_if_not_found=False)`` of them degrades
  silently.
* A ``<field name>`` appears once per record (``duplicate-field``); the loader
  keeps the last and the earlier one is dead.
* ``eval=`` parses as Python and is never empty (``eval-syntax``); an x2many
  ``eval`` writes ``Command.set/link/create/...``, not the ``(6, 0, ...)``
  tuples (``legacy-x2many-command``) ``[fixer _modernize_commands]`` -- run
  ``odoo/addons/test_lint/tests/_modernize_commands.py <dir>``, then the sorter
  and the formatter.
* Every ``model`` a record, view or action names has a ``_name`` in the tree
  (``unknown-model``).
* Every reference the loader resolves at install resolves statically
  ``[test_lint test_record_refs]``: ``ref=``, ``ref()`` in ``eval``/
  ``context``/``search``, ``%(xmlid)d`` inside an arch or a ``<template>``,
  ``<template inherit_id>``, ``<menuitem parent/action>``, ``<delete id>``.

3.2 XML IDs
-----------

**Prefix style** -- role first, entity second ``[review]``. It matches Odoo
Community core, so new records sit beside the core records they relate to.

.. list-table::
   :header-rows: 1

   * - Type
     - Pattern
     - Example
   * - Views
     - ``view_{model}_{type}``
     - ``view_sale_order_form``
   * - Inherited views
     - ``view_{model}_{type}_inherit_{context}``
     - ``view_sale_order_form_inherit_custom``
   * - Actions / server actions
     - ``action_{name}``
     - ``action_sale_order``
   * - Menus
     - ``menu_{name}``
     - ``menu_sale_order``
   * - Groups
     - ``group_{name}``
     - ``group_sale_manager``
   * - Record rules
     - ``{model}_rule_{group}``
     - ``sale_order_rule_portal``
   * - Report actions
     - ``action_report_{name}``
     - ``action_report_saleorder``
   * - Report templates
     - ``report_{name}_document``
     - ``report_saleorder_document``
   * - Email templates
     - ``mail_template_{name}``
     - ``mail_template_sale_confirmation``

A few legacy core ids are model-first (``sale_order_menu``, ``sale_menu_root``)
and multi-company rules keep the core ``{model}_comp_rule`` form. Leave them;
``ref`` their real id.

3.3 Views
---------

**Form**

.. code-block:: xml

   <form>
     <header>
       <button string="Confirm" name="action_confirm" type="object"
               invisible="state != 'draft'" class="oe_highlight"/>
       <field name="state" widget="statusbar"/>
     </header>
     <sheet>
       <div name="button_box"/>
       <div class="oe_title"><h1><field name="name"/></h1></div>
       <group name="main">
         <group name="left_col"/>
         <group name="right_col"/>
       </group>
       <notebook>
         <page string="Lines" name="lines"/>
       </notebook>
     </sheet>
     <chatter/>
   </form>

**List** -- ``<list>``, never ``<tree>`` (``tree-view``):

.. code-block:: xml

   <list multi_edit="1">
     <field name="name"/>
     <field name="amount_total" sum="Total"/>
     <field name="state" decoration-success="state == 'done'"/>
     <field name="technical_field" column_invisible="True"/>
     <field name="optional_field" optional="hide"/>
   </list>

**Search** -- inside a ``<search>``, ``<group>`` no longer accepts ``string`` or
``expand``; both are rejected by view validation, while ``name``, ``invisible``,
``groups`` and ``colspan`` remain valid (the RNG is
``odoo/addons/base/rng/common.rng``). Every group and every filter needs a
``name``, so inheritance can reach it by XPath (``search-item-name``). A
group-by filter carries no ``domain`` -- the client promotes it to a
``groupBy`` item and never reads one (``groupby-filter-domain``):

.. code-block:: xml

   <search>
     <field name="name"/>
     <filter string="Draft" name="draft" domain="[('state', '=', 'draft')]"/>
     <separator/>
     <filter string="My Orders" name="my_orders" domain="[('user_id', '=', uid)]"/>
     <group>
       <filter string="Partner" name="group_partner" context="{'group_by': 'partner_id'}"/>
     </group>
   </search>

**Kanban** -- the card template is ``t-name="card"`` (``kanban-box``), and the
CSS classes are ``card`` and ``menu`` (not ``kanban-card`` / ``kanban-menu``).
Each ``t-name`` is its own OWL template: a ``t-set`` in ``menu`` is not visible
in ``card`` (``kanban-template-scope``):

.. code-block:: xml

   <kanban default_group_by="state">
     <templates>
       <t t-name="card">
         <div class="card">
           <field name="name"/>
         </div>
       </t>
     </templates>
   </kanban>

Across every view type: put ``name=""`` on groups, pages and divs so inheritance
has something stable to target -- and one name per arch, since an xpath by name
reaches only the first and ``search_default_<name>`` toggles every filter of
that name (``duplicate-arch-name``). Write conditions as Python expressions
(``invisible=``, ``readonly=``, ``required=``) that parse -- an empty one is
dead and belongs off the element (``expression-syntax``) -- spelled ``True`` /
``False``, not ``true`` (``boolean-spelling``). ``attrs=`` and ``states=`` were
removed in 17.0 (``removed-attribute``); fields referenced only by an
expression are auto-injected. ``optional=`` is ``show`` or ``hide``
(``optional-value``). Dead attributes the renderer never reads are findings:
``nolabel=`` outside a ``<group>``/``<setting>`` (``nolabel-outside-group``),
``column_invisible=`` in a form (``column-invisible-outside-list``),
``readonly=`` equal to ``invisible=`` (``readonly-duplicates-invisible``),
``type=`` beside ``special=`` on a button (``special-button-type``).

3.4 Wizards
-----------

TransientModel views live in ``wizards/``. No ``<sheet>``, no ``<header>``, no
``<chatter/>``; buttons go in ``<footer>``. ``res.config.settings`` is a wizard
and belongs here.

.. code-block:: xml

   <form>
     <group>
       <field name="partner_id"/>
       <separator string="Options"/>
       <field name="option_ids" nolabel="1"/>
     </group>
     <footer>
       <button string="Apply" name="action_apply" type="object" class="btn-primary"/>
       <button string="Cancel" special="cancel"/>
     </footer>
   </form>

3.5 Inheritance
---------------

.. code-block:: xml

   <record id="view_sale_order_form_inherit_custom" model="ir.ui.view">
     <field name="name">sale.order.form.inherit.custom</field>
     <field name="model">sale.order</field>
     <field name="inherit_id" ref="sale.view_sale_order_form"/>
     <field name="arch" type="xml">
       <xpath expr="//field[@name='partner_id']" position="after">
         <field name="custom_field"/>
       </xpath>
     </field>
   </record>

Prefer ``name=`` targets over positional XPath; the expression must compile
(``xpath-syntax``). Positions are ``inside``, ``after``, ``before``, ``replace``
and ``attributes``; ``position="replace"`` with empty content deletes an
element. ``hasclass()`` targets by CSS class. Under ``position="attributes"``
only ``<attribute>`` children are read (``attributes-spec-child``): a
``<field>`` there is never added, and a ``<t t-if>`` around an ``<attribute>``
guards nothing.

3.6 QWeb reports
----------------

Three parts -- document template, wrapper, action:

.. code-block:: xml

   <template id="report_sale_order_document">
     <t t-call="web.external_layout">
       <div class="page"><!-- content --></div>
     </t>
   </template>

   <template id="report_sale_order">
     <t t-call="web.html_container">
       <t t-foreach="docs" t-as="doc">
         <t t-call="module.report_sale_order_document"/>
       </t>
     </t>
   </template>

   <record id="action_report_sale_order" model="ir.actions.report">
     <field name="name">Sales Order</field>
     <field name="model">sale.order</field>
     <field name="report_type">qweb-pdf</field>
     <field name="report_name">module.report_sale_order</field>
     <field name="binding_model_id" ref="sale.model_sale_order"/>
     <field name="binding_type">report</field>
     <field name="binding_view_types">list,kanban</field>
   </record>

Output with ``t-out``; ``t-esc`` and ``t-raw`` log a deprecation on every
compile (``deprecated-output-directive``) ``[fixer _modernize_output_directives]``
-- the fixer renames ``t-esc``; ``t-raw`` skips escaping and is rewritten by hand.
An xpath that locates by ``@t-esc`` follows the rename.

``report_name`` is required and points at the QWeb template. ``report_file`` is
optional -- a PDF base-filename hint core often omits. ``binding_type`` is
``"report"`` (Print menu) or ``"action"``; ``binding_view_types`` is
order-significant and is most often ``list,kanban``. Use ``t-lang=`` at the
``t-call`` level to localise.

3.6.1 PDF rendering is WeasyPrint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This fork renders ``qweb-pdf`` with **WeasyPrint** and real CSS Paged Media;
wkhtmltopdf is gone, and so is its folklore. The engine is ``WeasyPrintEngine`` in
``addons/web/models/ir_actions_report.py``, an ``_inherit`` of the action type
``base`` declares: ``base`` owns the record, the bindings and the HTML and text
renders, ``web`` owns every PDF path, ``report.layout``, the company's
document-layout fields and the templates the PDF is poured into
(``web.minimal_layout``, ``web.external_layout``). The paged-media CSS is
``addons/web/static/src/webclient/actions/reports/report_paged_media.css`` and
``report_pdf_layout.css``.

**Layout**

* Bootstrap **5** class names only. ``text-right`` / ``text-left`` no longer exist
  and fail silently -- use ``text-end`` / ``text-start``, ``float-end``, ``ms-*`` /
  ``me-*``.
* Responsive breakpoints (``col-md-*``, ``d-md-*``) are meaningless in paged media.
  Core layouts branch on ``report_type == 'pdf'`` and use CSS Grid there
  (``o_report_header_*``, ``o_report_footer_grid``). Do not lay out with
  ``<table>``.
* Report CSS goes in an SCSS file added to ``web.report_assets_common``, not in
  inline ``<style>`` blocks or ``style=`` attributes. Consume the per-company
  design tokens (``--co-primary``, ``--co-font``, ``--rp-*``) instead of
  hard-coding colours.

**Paperformat**

Live fields: ``format`` / ``page_width`` / ``page_height``, ``margin_*`` (mm),
``orientation``, ``header_line``, ``css_margins``. ``dpi``, ``header_spacing`` and
``disable_shrinking`` still exist on the model but are wkhtmltopdf-era and inert
-- do not set them on new paperformats. Header and footer size is controlled by
``margin_top`` / ``margin_bottom``; the ``.header`` and ``.footer`` divs become CSS
running elements in the page margin boxes.

**Paged-media toolbox**

* Page numbers: ``<span class="page"/>`` and ``<span class="topage"/>``, backed by
  CSS counters. Never JavaScript.
* Break control: ``o_page_break_before`` / ``o_page_break_after``,
  ``break-inside: avoid``, and ``o_thead_no_repeat`` to stop a ``<thead>``
  repeating on long tables.
* PDF outline: ``bookmark-level`` is set on ``h2[name="document_title"]`` and
  ``h3[name]``, so real headings give multi-record batches a navigable outline.
* Also supported, and preferable to hacks: ``string-set`` running headers,
  ``target-counter()`` with ``leader('.')`` for tables of contents, named
  ``@page`` rules for landscape annexes, and ``float: footnote``.
* PDF/A-3 with Factur-X and XMP metadata is native -- see ``_prepare_pdf_options``.
  The same ``data["__pdf_options__"]`` channel takes ``dpi`` and ``jpeg_quality``,
  the two file-size levers for image-heavy reports.

**Engine services** -- no template work required

* **Metadata**: ``/Title`` is the evaluated ``print_report_name`` (falling back to
  the action label); ``/Author`` the company, ``/Creator`` ``Odoo``, ``/Lang`` the
  record's language, which also switches on ``hyphens: auto``.
* **Watermark**: ``with_context(report_watermark="DRAFT")`` stamps text diagonally
  on every page of that print.
* **Themes**: ``report.theme`` (Settings → General → Document Layout) emits the
  ``--rp-*`` tokens per company via ``web.styles_company_report``.
* **Diagnostics**: WeasyPrint CSS warnings are captured per render. A failed
  render names the offending rule in its ``UserError``; successful renders log
  warnings at DEBUG.

In test mode ``_render_qweb_pdf`` returns raw HTML unless
``force_report_rendering`` is set. Render-path tests are in
``addons/web/tests/test_report_rendering.py``.

3.7 Actions and menus
---------------------

.. code-block:: xml

   <record id="action_sale_order" model="ir.actions.act_window">
     <field name="name">Sales Orders</field>
     <field name="res_model">sale.order</field>
     <field name="view_mode">list,form</field>
     <field name="path">sales/orders</field>
     <field name="context">{"search_default_my_orders": 1}</field>
     <field name="domain">[('state', '!=', 'cancel')]</field>
     <field name="help" type="html">
       <p class="o_view_nocontent_smiling_face">Create a new sales order</p>
     </field>
   </record>

``view_mode`` is kanban-first for operational screens, list-first for admin and
reporting. ``path`` gives the action a readable URL. In XML domains use lists, not
tuples, and ``uid`` unquoted for the current user.

Every menuitem in a module goes in ``views/<module>_menus.xml``, not scattered
across view files ``[fixer _relocate_menus]`` ``[ratchet lint_xml_menuitem_placement]``
-- the gate wants ``menu`` in the file name; ``ir_ui_menu_views.xml`` is where
``base`` keeps the views *of* ``ir.ui.menu``. The menus file is listed after
every file that defines an action a menu names -- last in ``data`` unless a
data file needs a menu first. A record that only exists to bind a menu -- an
``ir.actions.client`` whose ``params`` carry a ``menu_id``, an ``ir.ui.menu``
record patching an ``action`` onto a menu declared elsewhere -- lives in the
menus file too (or, for the patch, becomes the menuitem's own ``action=``):

.. code-block:: xml

   <odoo>
     <menuitem id="menu_sale_root" name="Sales" sequence="10"/>
     <menuitem id="menu_sale_order" name="Orders"
               parent="menu_sale_root" action="action_sale_order" sequence="1"/>
   </odoo>

**Contextual (gear) menus.** The gear menu and the selection *Actions* dropdown
render one grammar, sections in this order, a divider between non-empty ones.
Each section is a ``COG_GROUP`` constant from ``@web/search/cog_menu/cog_menu_group``;
a bare number is rejected by the ``cogMenu`` registry validation.

=======================  =============================================================
``COG_GROUP.DATA``       import and export: Import Records, Export All, Export…
``COG_GROUP.RECORD``     the record at hand: Edit Properties…, Duplicate, Archive
``COG_GROUP.APP``        the current app's own features
``COG_GROUP.PRINT``      reports
``COG_GROUP.ACTIONS``    server-bound actions (``binding_model_id``)
``COG_GROUP.INTEGRATE``  send the view elsewhere: Knowledge, Dashboard, Spreadsheet
``COG_GROUP.DANGER``     irreversible, alone and last: Delete
=======================  =============================================================

- Render items with ``CogMenuItem`` (``icon``, ``description``, ``danger``); a shared
  verb (``duplicate``, ``delete``, ``versionHistory``, ``insertInSpreadsheet`` …) is
  declared through ``prepareStaticActionMenuItems``, never restated as a raw object.
- Labels are Title Case and end with ``…`` when the item opens a dialog, wizard or
  file picker before acting ``[gate contextual_menu_title_case]``
  ``[gate contextual_menu_dialog_ellipsis]``. No "Print" prefix inside Print.
- Order bound actions with ``binding_sequence`` and give recurring verbs a
  ``binding_icon``; ``sequence`` on a server action orders child actions only.
- ``isDisplayed`` runs cheap synchronous checks first (``isActWindowView``), awaited
  group or RPC checks last; mobile exclusion goes through ``env.isSmall`` there, not
  in the template.
- ``u`` belongs to the gear; a view button never claims it
  ``[gate contextual_menu_hotkey_u]``.

3.8 Settings views
------------------

``<app>`` → ``<block>`` → ``<setting>``, in ``wizards/res_config_settings_views.xml``:

.. code-block:: xml

   <xpath expr="//form" position="inside">
     <app string="My Module" name="my_module">
       <block title="Features">
         <setting string="Feature X" help="Enable feature X">
           <field name="enable_feature_x"/>
         </setting>
       </block>
     </app>
   </xpath>

3.9 ``noupdate`` protects every write but the first
---------------------------------------------------

``noupdate="1"`` on an ``<odoo>`` or ``<data>`` block says *seed, do not manage*:
the records inside it are a starting point a database is then free to change.
Two halves of that follow, and each has cost a fix here.

**The install writes regardless of the flag** ``[review]``. ``convert.py`` gates
the skip on ``if self.noupdate and self.mode != "init"``, and a module being
*installed* loads its data with ``"init"`` (``modules/loading.py`` picks
``"update"`` only for an upgrade), so every record in the block is written --
including one whose xml id already names a record the database had. A
``pre_init_hook`` that hands a shipped xml id to an existing record, so the data
file updates it instead of creating a twin, therefore also hands that record's
fields to the data file for one write. ``fleet``'s brand catalogue adopts a
manufacturer partner of the same name this way; on a production copy that first
write replaced four logos the database already had and turned 77 partners into
companies. ``noupdate`` stops the *next* ``-u fleet`` from doing it again and
could not have stopped the first.

The rule behind that: **a data file carries only the fields the module owns.**
A field a user may have set on a record the module adopted is not one of them,
so it belongs in a ``post_init_hook`` writing the records the module itself
created, not in the data file.

**The stored flag is never refreshed** ``[review]``.
``ir.model.data._update_xmlids`` writes ``{"model", "res_id"}`` on an existing
row and never its ``noupdate`` column, so removing the attribute from the tree
reaches new databases only. A database that has the record keeps the flag it
stored at install, and correcting the record in the tree is not delivery: it
takes a **pre**-migration clearing ``ir_model_data.noupdate`` for that xml id,
which runs before the data files load, so the same upgrade rewrites the record.
Log how many rows still carried the broken content -- on a customer database
that count is the only evidence it was ever broken. This is why a renamed method
surviving inside a ``noupdate`` ``ir.cron`` needs a migration (§2.4.19).

**Neither half shows on a fresh database**, which is where nearly everything here
is tested: with no stored row there is nothing to freeze, and with no existing
record there is nothing for the install to overwrite. Both are green there while
wrong, so green is not evidence. The witness for both is ``-u <module>`` on a
restored production copy, and the question to ask before running it is which xml
ids the module hands over and which of them the database already has.

----

4. JavaScript
=============

4.1 Modules and files
---------------------

Colocate a component's ``.js`` and ``.xml`` in a feature folder
(``static/src/<feature>/<component>.js`` + ``.xml``). ES6 imports only, no
``require()``.

.. code-block:: javascript

   import { Component } from "@odoo/owl";
   import { registry } from "@web/core/registry";
   import { _t } from "@web/core/translation";

``/** @odoo-module **/`` is a **routing directive for the asset bundler**, parsed
from the first 500 bytes of the file by ``odoo/tools/assets/esm_graph.py`` -- not
a cosmetic header. Files under ``static/src`` and ``static/tests`` are routed by
path, so the bare form is optional there. Write it explicitly for a modifier, or
for a file outside those paths:

* ``@odoo-module ignore`` -- keep the file out of the ESM pipeline (a classic
  script or vendored library).
* ``@odoo-module native`` -- treat as a true native ES module.
* ``@odoo-module alias=<specifier>`` -- register under an additional import path.
* ``@odoo-module default=<name>`` -- control default-export bridging.

Two asset mistakes take a whole page down while the HTTP response stays ``200``,
because the pipeline degrades rather than raises, and neither is caught by a
module's own test suite:

* **Every ``@addon/...`` import must resolve to a file**
  ``[test_lint test_esm_specifiers]``. esbuild fails the *entire bundle* on one
  unresolvable specifier, and a failed build is served as an empty one -- so a
  module moved inside ``web`` blanks the web client of every database carrying an
  addon that still imports the old path. In a *test* file the same specifier
  registers no suite at all, so the run reports fewer tests rather than an error.
* **A bundle rendered by ``t-call-assets`` must be declared under the manifest's
  ``esm`` key if it carries ES-module sources** ``[test_lint test_esm_bundles]``.
  Undeclared, it is concatenated as legacy JS and every module-syntax file in it
  is replaced by a ``console.error`` stub, so the page boots into nothing. A
  bundle only ever ``('include', ...)``-ed into another needs no declaration.

Run both after any move, rename or new bundle -- about two seconds::

   odoo-bin -d <db> -i test_lint --test-enable --stop-after-init --no-http \
       --test-tags '/test_lint:TestEsmSpecifiers,/test_lint:TestEsmBundles'

Under ``--test-enable`` or ``--dev=assets`` a failed esbuild build **raises**
(``EsbuildBundleError``) instead of degrading to an empty bundle. A run that dies
naming a bundle is reporting the breakage that, in production, is a page loading
with no JavaScript. Fix the import or the declaration; do not ignore the bundle.
Escape hatch for a run that must survive a known-broken bundle:
``ir.config_parameter`` ``web.esbuild.fail_closed = 0``.

4.2 Naming
----------

* Components ``PascalCase``; methods and variables ``camelCase``.
* **When JS names a Python method, the string must match exactly.** An ORM call or
  a button ``name`` targeting ``action_view_invoices`` uses that name verbatim.
  This is about the call target, not about frontend handlers.
* Portal template ``t-name`` values follow the field naming conventions
  (``invoice_state``, not ``invoice_status``).

4.3 OWL
-------

4.3.1 Rules
~~~~~~~~~~~

* **``super.setup()`` first** when patching -- before anything else.
* **``useState`` for reactive state.** A plain assignment does not re-render.
* **Verify import paths.** Odoo moves components between releases; assume a
  recalled path is stale.
* **POS: ``t-inherit`` for markup, ``patch`` for behaviour.** Reserve
  ``onMounted`` DOM access for measurement and focus -- raw DOM injection breaks
  on re-render.

4.3.2 ``this`` in a template is not always the component
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OWL renders against a *derived* context, not the component
(``addons/web/static/lib/owl/owl.es.js``)::

   const ctx = Object.assign(Object.create(this.component), { this: this.component });

Template expressions compile to lookups on ``ctx``. Because ``ctx`` only
*inherits* from the component, **reads** always resolve, but a **write** to a bare
instance property lands on ``ctx`` -- a per-render throwaway, invisible to the
component and gone on the next render.

.. list-table::
   :header-rows: 1

   * - Reference in the template
     - ``this`` inside the member
     - Bare ``this.x = …``
   * - ``this.foo()``
     - the component
     - safe
   * - ``t-on-click="foo"``
     - the component -- invoked as ``handler.call(node.component, ev)``
     - safe
   * - ``onFoo.bind="foo"``
     - the component
     - safe
   * - ``foo`` / ``foo.bar`` (bare getter or method)
     - the derived ``ctx``
     - **lost**

Only the last row is dangerous, and it fails silently:

* ``this.someObject.key = v`` is safe everywhere -- the *read* resolves through
  the prototype chain to the component's object and the mutation lands on it. Only
  rebinding the property itself (``this.counter = 1``) is lost.
* A member reached transitively binds like its entry point: a bare template getter
  calling ``this.helper()`` still runs ``helper`` on ``ctx``.

When a bare template member must persist something, mutate a container object
created in ``setup()`` -- see ``Many2XAutocomplete.emptySearchMemo``.

4.3.3 Patching
~~~~~~~~~~~~~~

.. code-block:: javascript

   import { patch } from "@web/core/utils/patch";
   import { useService } from "@web/core/utils/hooks";
   import { useState, onWillStart } from "@odoo/owl";

   patch(ProductCard.prototype, {
       setup() {
           super.setup(); // always first
           this.orm = useService("orm");
           this.customState = useState({ data: null });
           onWillStart(async () => {
               this.customState.data = await this.orm.call(
                   "product.product", "custom_read", [],
               );
           });
       },
   });

Choosing an approach:

.. code-block::

   Change the markup of an existing component?   -> t-inherit the template
   Change its behaviour?                          -> patch(Component.prototype, {...})
   New UI element?                                -> new OWL component + registry entry
   Unsure?                                        -> read reference/owl/ before guessing

4.4 Tests
---------

Frontend changes ship with a test ``[review]``. QUnit is removed -- do not write
it.

* **Unit and component tests -- Hoot.** ``static/tests/**/*.test.js``, importing
  from ``@odoo/hoot`` and ``@odoo/hoot-dom``, with the mock server for ORM calls.
  This is the default.

  .. code-block:: javascript

     import { expect, test } from "@odoo/hoot";
     import { click } from "@odoo/hoot-dom";

     test("counter increments on click", async () => {
         await click("button.increment");
         expect("span.value").toHaveText("1");
     });

* **Integration and end-to-end -- tours.** Register in the ``web_tour.tours``
  registry and drive from a Python ``HttpCase`` tagged
  ``@tagged("post_install", "-at_install")`` via
  ``self.start_tour(url, "tour_name", login=...)``. Use tours for flows spanning
  backend and UI.

Two operational facts about the Hoot runner:

* **The unit-test bundle is not rebuilt while the server runs** -- not for XML,
  not for a new ``.test.js``, not for a plain source edit. Restart the server after
  every change; a green run only proves the bundle you built.
* **An import failure reads as a lower pass count, never as a failure.** Read the
  import-failure line rather than trusting "Passed N".

JavaScript is also covered by the ESLint and ``tsc`` ratchets. Neither is expected
to be clean; neither may get worse.

----

5. CSS / SCSS
=============

5.1 Naming and organisation
---------------------------

* Module-prefixed classes: ``.o_module_name_element``.
* Files in ``static/src/scss/``, or colocated with the component they style.
* Declared in ``__manifest__.py`` under ``assets``, in the bundle that loads where
  the style is needed. Wrong-bundle CSS either does nothing or bloats every page.

.. list-table::
   :header-rows: 1

   * - Bundle
     - Loads in
   * - ``web.assets_backend``
     - backend web client -- most module UI
   * - ``web.assets_frontend``
     - website and portal
   * - ``point_of_sale._assets_pos``
     - Point of Sale client
   * - ``web.report_assets_common``
     - QWeb PDF reports
   * - ``web._assets_primary_variables``
     - SCSS variable **overrides**, loaded first; emits no rules

5.2 Theming
-----------

* **Bootstrap first.** The UI is Bootstrap 5 -- reuse its utilities and components
  before writing SCSS.
* **Override variables, not values.** Customise through Odoo and Bootstrap SCSS
  variables injected into ``web._assets_primary_variables`` (or
  ``_secondary_variables``). Never hard-code a colour or spacing a variable
  already controls.
* **Dark mode** is file-based: a ``*.dark.scss`` sibling is globbed automatically
  into ``web.assets_backend_dark`` / ``web.assets_web_dark``. Put dark overrides
  there and drive colours from variables.
* **RTL** is generated automatically. Use logical properties
  (``margin-inline-start``) and Odoo's RTL-aware mixins, not hard ``left`` /
  ``right``.

5.3 Browser floor
-----------------

**Current evergreen browsers. This fork does not support old ones, and no
declaration carries a fallback for them** ``[review]``. The JS floor is
``_ESBUILD_TARGET = "es2023"`` in ``odoo/tools/assets/esbuild.py``; the CSS floor
is stated here so authors stop guessing conservatively. Anything **Baseline newly
available** may be used directly, in every bundle, including the public ones:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Use
     - Instead of
   * - ``color-mix(in srgb, C N%, transparent)``
     - ``rgba($c, .N)`` -- Baseline *widely* available, the workhorse
   * - ``hsl(from C h s calc(l - 10))``
     - ``darken($c, 10%)`` -- reproduces the Sass value exactly, HSL for HSL
   * - ``light-dark(a, b)``
     - a one-off colour that differs by scheme and deserves no token name
   * - ``oklch(from C calc(l - .1) c h)``
     - a *deliberate* palette change: perceptually uniform, so a step looks the
       same on yellow as on blue. It does **not** reproduce ``darken()``

A Sass colour function resolves when the bundle compiles, which is why this fork
ships every stylesheet twice; the CSS equivalents resolve in the cascade, so one
stylesheet answers both colour schemes. ``test_lint``'s ``TestSchemeDuplication``
measures the distance still to go.

``contrast-color()`` is the exception, on semantics rather than support: it
returns only white or black, while ``o-scheme-contrast()`` picks among four
foregrounds. Contrast picks stay compile-time and published per scheme.

5.4 Moving a variable onto a token
----------------------------------

``o-token(--name, $fallback)`` turns a Sass assignment into a ``var()``, so the
value is decided in the cascade and one declaration answers both schemes. Two
things make a variable ineligible, and only the first announces itself
``[review]``:

* **It is read by Sass colour maths.** ``darken()``, ``mix()``, ``rgba()``,
  ``color-contrast()`` and friends take a colour, and a ``var()`` is not one.
  Sass raises ``$color: var(…) is not a color`` and the bundle fails to compile.
  Grep the whole workspace before converting -- ``$card-bg`` is read by
  ``color-contrast()`` from ``portal``, four addons away from where it is assigned.
* **It is interpolated into an SVG data URI.** ``$form-check-*-color`` reaches
  ``stroke='#{…}'`` inside ``url("data:image/svg+xml,…")``. A custom property
  there is inert: the URI is not CSS, so the ``var()`` neither resolves nor
  errors -- the compile succeeds and the icon simply stops being drawn, and
  nothing reports it. Convert the variable only alongside the image that reads it.

The same applies to a value handed to a mixin: ``o-button-variant-from()`` and
``o-print-color-rgb()`` accept tokens deliberately and say so, but a mixin written
for colours will fail on the first function it reaches.

5.5 Restating a rule for the other scheme
-----------------------------------------

Where neither a token nor ``light-dark()`` can carry a value -- a
``color-contrast()`` pick, a ``shift-color()``, a variable a colour function reads
-- the rule is restated under ``:root[data-color-scheme="dark"]``, which outscores
the plain rule (0,2,0) against (0,1,0). ``scheme_rules.scss`` and
``html_editor.scheme_rules.scss`` are where those live ``[review]``.

* **One rule per original rule, with its whole selector list.** Grouping three of
  Bootstrap's ``:focus`` rules into one scoped rule answers *none* of them, and
  ``.navbar-dark`` alone does not answer
  ``.navbar-dark,.navbar[data-bs-theme=dark]``. Copy the selector as the bundle
  emits it.
* **Only the dark half.** Whatever emits the light half already did so.
* **Screen only.** ``assets_web_print`` includes the backend bundle and is linked
  unconditionally, so an unscoped block answers the attribute in print.
* **Not where it cannot apply.** A file riding ``assets_frontend`` should not
  carry the dark half, since nothing there sets the attribute. Split it into a
  sibling declared in the backend bundle alone, as
  ``html_editor.scheme_rules.scss`` is.
* **Never call ``tint-color()`` or ``shade-color()`` from a scoped block.** The
  dark bundle carries ``bs_functions_overridden.dark.scss``, which redefines both
  -- in dark, tint mixes with *black* -- so calling Bootstrap's own function from
  a light bundle computes the light meaning of the word and the two bundles
  disagree about a colour they both call dark. Use ``o-scheme-tint(…, $-scheme)``
  / ``o-scheme-shade(…, $-scheme)``, which take the mix colour from the scheme.
* **``@extend`` does not compose with a scope** unless what the placeholder emits
  carries no colour, in which case the light half already answers and the dark
  half must omit it. See ``o-bg-color()``'s ``$extend-heading-reset``.

5.6 Weighing a conversion
-------------------------

**Weigh the bytes.** A ``var(--name, <fallback>)`` is longer than the colour it
replaces, once per use, and a variable already flattened into a string by the time
the token reaches it buys nothing -- ``$focus-ring-color`` cost 34 KB on every
backend bundle for that reason. Read the compiled size alongside
``TestSchemeDuplication``'s count; a conversion that moves neither is one to
drop.

----

6. Tests
========

6.0 Choosing a tier
-------------------

The framework ships three tiers. Pick the lightest one that can express the test;
§6.1 onwards concerns Tier 3, which is what most addon tests use.

.. list-table::
   :header-rows: 1
   :widths: 16 34 50

   * - Tier
     - Entry point
     - Use when
   * - **1 -- Component**
     - ``odoo/orm/components/tests/`` and the other ``pytest`` suites
     - Exercising ORM algorithms in isolation -- cache, compute scheduling, flush
       convergence, trigger graph -- against the real component objects. No
       fields, no ``@api.depends``, no ``odoo`` imports. Milliseconds.
   * - **2 -- ORM, database-free**
     - ``model_test_env`` / ``ModelRegistry`` (``odoo/orm/model_test_env.py``)
     - Real model methods, real ``@api.depends`` computes and real ``Field``
       descriptors against an in-memory backend. No PostgreSQL.
   * - **3 -- Integration**
     - ``TransactionCase`` / ``HttpCase``
     - Anything needing SQL, ACLs, several modules, or the web client.

Tier 1's hand-rolled dependency graph *is* the subject under test; not reusing
Tier 2's real ORM is intentional, not duplication.

Tiers 1 and 2 are plain ``pytest`` and need **two invocations** -- Tier 1
registers process-global ``sys.modules`` stubs that would shadow Tier 2's real
imports:

.. code-block:: bash

   cd <odoo repo>

   pytest                                          # Tier 1 (config: pytest.ini)
   pytest odoo/orm/tests odoo/http/tests odoo/db/tests odoo/tools/tests \
       tests/service tests/framework                                     # Tier 2

Pass **all six** Tier-2 paths. None is in Tier 1's ``testpaths``, so a shorter
command silently skips whole suites and still reports success.

``tests/framework`` holds the gates that assert things about the real ``odoo.*``
packages themselves -- that every public facade declares ``__all__``, and that
every monkeypatch is applied whatever the import order. They cannot be Tier 1:
the stubs would replace the objects under test.

Three further suites sit outside the tiers because they need real resources:

.. code-block:: bash

   pytest tests/contract   # needs PostgreSQL + psql/pg_dump on PATH; <1s
   pytest tests/process    # boots real odoo-bin processes; POSIX + PostgreSQL; ~20s
   pytest tests/loading    # installs base into a scratch DB; the slowest

**Contract tests** pin the behaviour of our *dependencies* -- psycopg's exception
hierarchy, what ``pg_dump`` emits, how ``psql`` lexes a meta-command, whether
``Popen`` closes its pipes -- not our own logic. A mock encodes the same belief as
the code it stands in for, so it cannot catch a wrong one. Write a contract test
whenever code branches on how a dependency behaves, and assert the dependency
directly, so a version bump fails in a test that *names the assumption*. The suite
skips when a dependency is missing, so a green local run may have compared
nothing; set ``ODOO_CONTRACT_REQUIRE_DEPS=1`` to make a missing one fail.

**Process tests** assert only what an outside observer can see: a listening port,
a process tree, an HTTP response. The suite is deliberately tiny -- the service
layer is covered far more cheaply by the mock-based suites in ``tests/service``.
Add one only for behaviour that emerges from real processes and vanishes the
moment anything is mocked. Two rules keep it from rotting:

* Assert on observables, never on internal state -- otherwise it is a slow unit
  test.
* **Readiness is a served request, never a log line.** ``ThreadedServer.run``
  spawns the HTTP server and logs "HTTP service running" *before*
  ``preload_registries``, both under ``Registry._lock``, so the socket accepts and
  the log claims readiness while requests still block.

6.1 Layout and base classes
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Base class
     - Use for
   * - ``TransactionCase``
     - standard ORM tests; each method runs in its own rolled-back transaction
   * - ``SingleTransactionCase``
     - tests deliberately sharing state across methods
   * - ``HttpCase``
     - controllers, web UI, headless Chrome; tag
       ``@tagged("post_install", "-at_install")``

Tests live in ``tests/``, one file per feature, and **every file must be imported
exactly once from ``tests/__init__.py``** ``[test_lint test_test_holes]``. A file
that is never imported never runs and reports nothing, hence a hard gate.

.. code-block::

   tests/
     __init__.py          # from . import test_sale_order, test_sale_order_line
     test_sale_order.py
     test_sale_order_line.py

Naming: files ``test_<feature>.py``, classes ``TestFeatureName``, methods
``test_<specific_scenario>``.

6.2 Isolation
-------------

* **Create records in ``setUpClass()``** -- it runs once per class, not once per
  method. Use ``setUp()`` only when a method genuinely mutates shared state.
* **Freeze time.** ``datetime.now()`` makes tests flaky; use
  ``odoo.tests.freeze_time``.
* **Mock external services.** Tests run offline.
* **Test with minimal permissions** -- a user in only the group under test
  surfaces access-rule bugs early. ``@users("demo")`` covers multi-user cases.
* **A fixture that reuses a shipped record states every setting it relies
  on** ``[review]``. Demo data may have reconfigured the record before the
  test runs, and a suite that is green without demo can be red with it:
  ``approval``'s tests cleared ``approver_ids`` on
  ``approval_category_data_business_trip`` and added one approver, while the
  demo had set ``approval_minimum`` to 2 and ``approve_sequentially`` on the
  same category -- 33 errors under ``--with-demo``, none without. Reset the
  minimum and the sequencing beside the approvers, or build the record with
  the class's own helper. Logins collide the same way: a test user named
  ``approver1`` fails ``setUpClass`` on a database whose demo created one.
  And so do windows: ``approval_sale``'s rate-limit tests counted the orders
  the superuser had created in the last 24 hours, which on a demo database
  are the demo's -- create the records under test as a user of your own.
* **Never call ``cr.commit()``.** Test data lives in the test transaction and is
  rolled back; a commit permanently pollutes the database. The one exception is a
  concurrency or cron test that deliberately opens ``self.registry.cursor()``.
* A test class is **either ``at_install`` or ``post_install``**, never both and
  never neither ``[review]``. Pure ORM tests are ``at_install``; anything touching
  other modules, the web client or tours is ``post_install``. ``@tagged`` only
  *warns* on a violation and the run proceeds, so a class tagged both ways is
  caught by review or not at all.

.. code-block:: python

   @classmethod
   def setUpClass(cls):
       super().setUpClass()
       cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})

6.3 ``BaseCommon``
------------------

``odoo.addons.base.tests.common.BaseCommon`` gives a quiet environment with mail
and tracking disabled. Not the default -- most tests still use ``TransactionCase``
-- but the right base class when mail noise is irrelevant.

It provides ``DISABLED_MAIL_CONTEXT``; pre-built ``cls.company``, ``cls.currency``,
``cls.partner``; the groups ``cls.group_user`` / ``cls.group_portal`` /
``cls.group_system``; and the helpers ``quick_ref(xmlid)``, ``_create_partner()``,
``_create_new_internal_user()``, ``_create_new_portal_user()``. It does **not**
create an independent user or company by default -- ``setup_independent_user`` and
``setup_independent_company`` return ``None`` unless a subclass overrides them.

6.4 Structure and completeness
------------------------------

Structure each test as setup → action → assertion, separated by blank lines.

.. code-block:: python

   def test_order_confirmation_sets_date(self):
       order = self.env["sale.order"].create({
           "partner_id": self.partner.id,
           "order_line": [Command.create({"product_id": self.product.id})],
       })

       order.action_confirm()

       self.assertEqual(order.state, "sale")
       self.assertTrue(order.date_order)

* Use specific assertions (``assertEqual``, ``assertIn``, ``assertRaises``) rather
  than bare ``assertTrue`` / ``assertFalse``.
* **Negative tests are mandatory** ``[review]``: every test class covers at least
  one expected-failure path -- a constraint raising ``ValidationError``, an
  unauthorised user getting ``AccessError``, an invalid state transition refused.
* **Parameterise with ``subTest()``**, so one failing case does not mask the rest:

  .. code-block:: python

     for amount, rate, expected in cases:
         with self.subTest(amount=amount, rate=rate):
             self.assertAlmostEqual(
                 self.env["account.tax"]._compute_amount(amount, rate), expected, places=2,
             )

* Use the ``Form`` simulator (``from odoo.tests import Form``) to test onchange
  behaviour without HTTP.
* **Lock hot paths with ``assertQueryCount``.** ``@warmup`` primes caches first.
* **Pin the shape before the number** ``[review]``. An absolute count moves
  with the installed modules, the demo data and every constant-cost change;
  what a batch must never do is grow with its size.
  ``self.assertQueriesConstant(run, small=2, large=40)`` runs ``run(n)`` at
  both sizes (each in a savepoint, after a warm-up run) and fails when the
  counts differ, so an N+1 fails whatever the pin says and a constant-cost
  change passes whatever the pin says. Keep the absolute pin beside it for
  the constant itself.
* **A moved count is a question, not a verdict** ``[review]``. A count changes
  when the work *moves* as readily as when it grows, and only the stack of the
  extra calls tells those apart: a pin asserting *exactly* one QWeb compile per
  batch reads **0** once the compiled template outlives the call, which is a fix
  landing rather than a regression. **Get the stack before moving a pin**, then
  move it and say in the commit what each unit bought.
* **Pin the guarantee, not the arithmetic** ``[review]``. Assert a bound, then
  assert the mechanism. ``assertEqual(compiles, 1)`` breaks the day caching
  improves it to zero; ``assertLessEqual(compiles, 1)`` followed by a second
  render asserting zero says *compiled once, never again*. **Both halves are
  required: a bound alone is satisfied by the work not happening at all.**

6.5 Raw SQL in tests
--------------------

The ORM defers writes, so flush before asserting on database state:

.. code-block:: python

   self.order.write({"state": "sale"})
   self.order.flush_recordset(["state"])
   self.env.cr.execute("SELECT state FROM sale_order WHERE id = %s", (self.order.id,))
   self.assertEqual(self.env.cr.fetchone()[0], "sale")

6.6 Lint relaxations in tests
-----------------------------

``ruff.toml``'s ``**/tests/**`` entry is the authority; read it rather than this
list. It suppresses ``B017`` (broad ``assertRaises``), ``RUF015``, ``PLW0603``,
``T201`` (``print``), ``PLR6201``, ``S110``, ``S113`` (HTTP without timeout),
``TRY002``, ``TRY203``, ``EM101``, ``PLR0124`` (self-comparison), ``A001`` /
``A002`` (builtin shadowing), ``RUF069`` (exact float assertions of deterministic
values), ``FURB152`` (fixture data that looks like a maths constant), ``B018`` and
``B015`` (a field touch or an ``in`` under ``assertRaises`` *is* the assertion),
and ``RUF075`` (post-``yield`` code is the assertion).

``ANN``, ``ARG``, ``FBT003``, ``RUF012`` and ``S301`` are also exempt inside
``odoo/libs/`` and ``odoo/orm/components/`` tests.

6.7 Tagging
-----------

* Default: ``standard`` + ``at_install``.
* ``HttpCase``: ``@tagged("post_install", "-at_install")``.
* **``at_install`` means the registry as the module is installed, and the
  loader keeps that promise on an installed database too** ``[review]``. On a
  fresh ``-i`` a module's suite runs the moment it loads, in the partial
  registry upstream describes. On a database where a *dependent* is already
  installed -- ``--test-tags /hr`` or ``-u hr`` with ``hr_work_entry`` present
  -- that registry cannot represent the table: ``hr_version`` carries
  ``date_generated_from NOT NULL`` and no loaded field to fill it, so every
  fixture that created an employee died. The loader now defers such a suite
  until the installed dependents that depend on the module are loaded, and
  says so (``Module hr: 36 at_install test(s) deferred until …``). A dependent
  marked *to install* has no column yet and does not defer, so a fresh install
  is unchanged. A test that passes at install and fails deferred has found a
  real interaction with a dependent, which is information, not noise.
* Slow or external tests excluded from the standard run: ``@tagged("-standard")``,
  optionally with a real selector tag such as ``external`` or ``nightly``. There
  is no ``heavy`` tag -- do not invent one.
* **Localisation tests** carry exactly one of ``post_install_l10n`` or
  ``external_l10n``, each paired with its base tag ``[test_lint test_l10n]``.
* **JS (HOOT) tests** carry ``desktop``, ``mobile`` or ``headless`` -- via
  ``test.tags(...)`` or a file-level ``describe.current.tags(...)`` ``[review]``.
  A test that mounts nothing and imports no ``@odoo/hoot-dom`` is ``headless``;
  one that branches on viewport or touch is ``desktop`` or ``mobile``. Leaving a
  test untagged is not neutral: it runs in *both* passes, so a DOM-free test pays
  a second run at 375x667 that can only repeat the first. ``headless`` still runs
  in the desktop pass -- it means DOM-free, not "no browser".

6.8 Coverage
------------

Aim above **80%** on custom modules -- aspirational, not gated. Cover edge cases,
constraints and validations, and give every ``action_*`` method at least one test.

.. code-block:: bash

   # a module's tests, during (re)install
   odoo-bin -d <db> -i <module> --test-enable --test-tags /<module> --stop-after-init

   # one class or method
   odoo-bin -d <db> --test-enable --test-tags /<module>:TestClass.test_method --stop-after-init

   # the post_install (HttpCase / tour) phase
   odoo-bin -d <db> -i <module> --test-enable --test-tags post_install --stop-after-init

   # coverage
   coverage run odoo-bin -d <db> -i <module> --test-enable --test-tags /<module> --stop-after-init
   coverage report

Two traps. Redirecting server output with ``>`` drops and reorders lines (Odoo
writes from several file descriptors without ``O_APPEND``) -- use ``>>``, ``tee``
or ``--logfile``, and gate on the exit code plus the ``N failed, M error(s)``
summary. And stopping a background run kills only the shell: ``odoo-bin`` survives
and keeps holding its HTTP port.

6.9 Pre-existing failures
-------------------------

**Do not re-run a suite to find out whether a red test was already red.** Diff
the run's failure *names* against a run of the same suite at ``HEAD`` in a
detached worktree ``[review]``. (``tooling/testbaseline`` kept a recorded
failure set per suite and diffed against it; it went with ``tooling/`` on
2026-09-11, and its expected-failure files with it.)

Two rules the tool exists to enforce, both measured rather than assumed:

- **Never count failures by grepping for** ``ERROR``. PostgreSQL error text is
  embedded verbatim in log records of *passing* tests, so a test that provokes a
  bad ``COPY`` contributes a line reading ``ERROR: ...``; on one ``/base`` log that
  grep answered 14 against a truth of 3. Anchor on the structured record
  ``<ts> <pid> ERROR uid:... <logger>: FAIL|ERROR: <Class.method>``, or on the
  server's own ``N failed, M error(s) of T tests`` summary.
- **Diff failure names, never counts.** ``quality_control`` held at two failures
  across a day in which one recorded test was fixed and an unrecorded one broke:
  a matching count reads as "both known" and ships the regression.

A suite with no recorded set gets no verdict rather than a guess.

----

7. Git
======

7.1 Commits
-----------

Subject line ``[TAG] module: description`` -- aim for 50 characters, hard cap 72,
and keep it shorter than the PR title.

``module`` is a single module (``account_cfdi``, or with a sub-path such as
``stock/routes``), a comma-separated list when the change genuinely spans several
(``[FIX] sale,purchase: ...``), or ``*`` for a tree-wide change. Prefer ``*`` over
an unreadable list.

**Thirteen tags, no others.** The first seven are upstream Odoo's; the rest are
AgroMarin additions.

.. list-table::
   :header-rows: 1

   * - Tag
     - Use for
   * - ``FIX``
     - bug fix
   * - ``IMP``
     - improvement to existing functionality
   * - ``ADD``
     - new module or feature
   * - ``REM``
     - removal of code, files or resources
   * - ``REF``
     - refactor, no behaviour change
   * - ``MOV``
     - file relocation (use ``git mv``)
   * - ``REV``
     - revert
   * - ``REL``
     - release / version bump
   * - ``MERGE``
     - merge commit
   * - ``I18N``
     - translation update
   * - ``PERF``
     - performance optimisation
   * - ``CLN``
     - cleanup, no functional change -- stricter than ``REF``
   * - ``LINT``
     - linting or formatting only

One primary tag per commit, chosen by dominant intent; if a change has two
intents, split it. ``LINT`` and ``CLN`` must contain no behaviour change -- if
they do, the tag is ``REF``.

.. code-block::

   [IMP] product_asset: filter Fleet views by fuel card

   Fleet and Fleet Service Logs showed all assets regardless of fuel card
   assignment, making the views noisy for operators.

   Solution:
   - Add domain filter on fuel_card_id to the Fleet list view
   - Apply the same filter to Fleet Service Logs

   Task ID: 17012

The ``Solution:`` block is mandatory. The ``Task ID`` line is **optional**: name
the task whenever the change has one, and leave the line out when it does not.
Never invent one, and never write ``Task ID: N/A``.

**Name files in a pathspec, never a directory** ``[review]``. ``git commit --
<path>`` records the *working tree* at that path, deletions included, and a
directory pathspec sweeps in every deletion under it:

.. code-block::

   rm research/note.md              # missing from the working tree

   git commit -m A -- research/keep.md    # note.md survives
   git commit -m B -- research            # note.md deleted, unmentioned

Name the files, and read ``git status`` for ``D`` lines before committing.

7.2 Branches and task IDs
-------------------------

Feature branches are ``<odoo_version>-t<task_id>-<github_username>``, e.g.
``19.0-t17352-suniagajose``, whenever the work has a task behind it. The task ID
on the branch and its commits is what traces a code change to a business
requirement.

Neither is required. Work with no task -- a hotfix, a chore, a guideline edit --
may be committed directly to the integration branch under a descriptive subject.
That is a normal outcome, not an exception to argue for afterwards.

7.3 Pull requests
-----------------

A PR is the default route and the only one that gets review, but it is **not
required**: a production hotfix, a small correction, or work its author owns end
to end may go straight to a shared branch. The knowledge repository works directly
on ``main`` in every case.

**Title**: ``[TAG] module: short description``, under 70 characters. For a
single-commit PR it mirrors the commit subject; for a change spanning modules, use
the dominant functional scope rather than a module list.

**Body**:

.. code-block:: markdown

   # [Task ID: XXXXX](https://$DOMAIN/odoo/project.task/XXXXX)

   ## Problem
   One to three sentences on what the user or system was experiencing.

   ## Solution
   - One bullet per logical unit of change, not per file

   ## Verification
   - Commands run, manual steps, or a checklist
   - `EXPLAIN ANALYZE` output for any new raw SQL (§11.6)
   - Screenshot or GIF for UI changes

Required:

* At least one commit per logical unit -- do not squash unrelated changes.
* No merge commits from the base branch in the PR history; rebase instead.
* No force-push to a **shared** branch (``main``, ``19.0``, ``19.0-marin``,
  ``19.0-dev``). Force-push is expected on your own feature branch.

Optional: the task-ID heading, as a **hyperlink** rather than plain text. Drop the
heading entirely when there is no task; do not leave ``XXXXX`` standing, and do
not write ``N/A``.

PRs land by **rebase merge**, which rewrites every SHA. Afterwards a local branch
reads "N ahead, N behind"; that is cosmetic. Confirm with
``git diff <local> origin/<branch>`` (empty means identical trees), then
``git reset --keep origin/<branch>`` -- ``--keep``, never ``--hard``: it preserves
uncommitted work and aborts rather than clobbering it.

Branch model: ``19.0`` is a pristine upstream mirror and never receives AgroMarin
work; ``19.0-marin`` is the integration branch; feature branches cut from and
merge back into it. The same model applies to the fork's other upstream mirror.

----

8. Translations
===============

8.1 Python
----------

Use ``self.env._()``. The legacy ``_()`` walks back up the call stack with
``inspect.currentframe()`` to infer the language and the calling module, which is
both slower and wrong where the frame above is not the one you think --
decorators, comprehensions, callbacks.

.. code-block:: python

   message = self.env._("Order confirmed successfully")
   raise UserError(self.env._("Order %s cannot be confirmed.", order.name))

Four rules, all enforced by ``_checker_gettext``, which recognises both ``_()``
and ``self.env._()``:

* **The first argument is a literal string** ``[test_lint E8502]``. A variable
  defeats extraction -- there is nothing for the exporter to find.
* **Two or more placeholders must be named** ``[test_lint E8503]``. With
  ``"%s of %s"`` a translator cannot reorder the arguments; write
  ``self.env._("%(done)s of %(total)s", done=x, total=y)``.
* **No ``%r``** ``[test_lint E8504]``. Its output is a Python repr, neither
  translatable nor meaningful to a user.
* **User-facing exceptions take a translated message** ``[test_lint E8505]``, not
  a bare literal (§2.7).

``ruff``'s ``INT`` rules match only the bare ``_()`` form, so ``test_lint`` is
what actually covers the form this guide mandates.

For constants declared outside a method, use ``LazyTranslate``:

.. code-block:: python

   from odoo.tools import LazyTranslate

   _lt = LazyTranslate(__name__)
   STATES = [("draft", _lt("Draft")), ("done", _lt("Done"))]

8.2 JavaScript and templates
----------------------------

.. code-block:: javascript

   import { _t } from "@web/core/translation";

   const message = _t("Operation completed");

Static string props on OWL components are extracted automatically
``[test_lint test_i18n, test_jstranslate]`` -- which means a user-facing string
assembled at runtime silently escapes translation. Keep literals literal.

A module with JS translations must register itself:

.. code-block:: python

   class IrHttp(models.AbstractModel):
       _inherit = "ir.http"

       @classmethod
       def _get_translation_frontend_modules_name(cls):
           return super()._get_translation_frontend_modules_name() + ["my_module"]

8.3 ``.pot`` / ``.po``
----------------------

Keep the template at ``i18n/<module>.pot`` and language files at
``i18n/<lang>.po``. Re-export after changing user-facing strings -- **including
deleting one**, or the template keeps advertising a message that no longer exists:

.. code-block:: bash

   odoo-bin --addons-path=odoo/addons,addons i18n export -d <db> <module>

Export through the **community trees only**, so the template lists only the
strings the community module ships. The header records ``odoo.release.series``
(``Odoo Server 19.0``): this fork's ``release.version`` is ``19.0+e`` on every
checkout, and an edition marker is a fact about the build, not about the
strings.

Never hand-edit a ``msgid`` to "fix" the English -- change the source string and
re-export. Duplicate entries in a ``.pot`` are a failure
``[test_lint test_pofile]``. Translations round-trip through Weblate
(``.weblate.json``); do not commit machine-merged ``.po`` churn that fights it.

----

9. Code review checklist
========================

What tooling cannot check. Do not re-verify lint codes by hand; skip an item that
does not apply, with a note.

**Security**

#. Dynamic SQL is parameterised or wrapped in ``SQL()`` -- including identifiers
   built from ORM metadata.
#. ``sudo()`` writes of user-submitted payloads whitelist the allowed fields.
#. Related fields reaching sensitive models (``ir.attachment``, ``hr.payslip``)
   have explicit access control (§10.5).
#. Every public method is *intentionally* an RPC endpoint.
#. Security validation uses ``if … raise``, never ``assert``.
#. Handlers expose no tracebacks or SQL fragments to users.
#. State-mutation code fails closed -- partial operations sit inside a savepoint.
#. No hard-coded URLs, credentials or service endpoints.

**Correctness**

#. No query call inside a loop over a recordset.
#. Computes assign fields directly; they never call ``write()``.
#. CRUD overrides call ``super()``; ``create`` uses ``@api.model_create_multi``.
#. ``@api.depends`` lists every sub-field the body reads --
   ``"partner_id.country_id"``, not ``"partner_id"`` (§11.4).
#. Every ``Monetary`` field has a currency field on the same model.
#. Error types match intent: ``UserError`` for business rules,
   ``ValidationError`` inside constraints, ``MissingError`` for deleted records.
#. ``.exists()`` is called where another transaction may have deleted the record.
#. Overridden framework methods carry ``@typing.override``.

**Performance**

#. Counts use ``search_count()``; aggregation uses ``_read_group()``.
#. No ``cr.commit()`` outside ``_commit_progress()``.
#. Crons batch with ``itertools.batched`` and ``_commit_progress()``.
#. Locking uses ``NOWAIT`` or ``SKIP LOCKED`` -- no unbounded waits.
#. New raw SQL ships ``EXPLAIN ANALYZE`` output in the PR description.
#. State-filtered tables use partial or expression indexes where they pay.

**Tests**

#. At least one negative test per test class.
#. No ``cr.commit()`` in tests.
#. Parameterised scenarios use ``subTest()``.
#. New test files are imported in ``tests/__init__.py``.

**Style**

#. External HTTP calls pass a ``timeout``.
#. Company and user come from ``self.env.company`` / ``self.env.user``.
#. Context is read with ``self.env.context.get()``, not direct indexing.
#. Methods stay under roughly 40 lines; longer logic is extracted.
#. Comprehensions use at most one ``for`` and one ``if``.
#. New code matches ``ruff format``'s style without reformatting the rest of the
   file (§2.1).

On complexity: ``max-complexity = 20`` is configured under ``[lint.mccabe]``, but
``C901`` sits in ``ruff.toml``'s ignore list on the deliberate grounds that Odoo's
ORM and QWeb methods are irreducibly branchy -- the ``c901`` ratchet re-selects it
on the CLI. Complexity is a review judgement in-file. Do not "fix" the config
without reversing that decision explicitly.

----

10. Security
============

10.1 Method visibility
----------------------

A public method -- no leading underscore -- is callable over XML-RPC and JSON-RPC
by any authenticated user. ACL checks happen during CRUD operations only; a custom
public method enforces nothing on its own.

* **Default every method to private.** Remove the underscore only after deliberate
  review.
* ``@api.private`` blocks RPC on a method that must keep a public *name*. It is
  enforced at the RPC boundary across the whole MRO, so a subclass cannot
  re-expose it. Use ``_`` for new code and ``@api.private`` to retrofit.

10.2 ``sudo()``
---------------

* **Prefer narrower escalation.** ``with_user(user)`` and ``with_company(company)``
  keep ACLs and record rules *enforced* under a different identity. Reserve
  ``sudo()`` for genuine cross-tenant or system operations.
* **Whitelist fields** when writing a user-submitted payload. A ``sudo()`` read of
  one field is low-risk; ``sudo().write(payload)`` is the dangerous shape.
* **Minimise scope** -- smallest recordset, fewest operations.

.. code-block:: python

   def action_update(self, values):
       allowed = {"description", "tag_ids"}
       self.sudo().write({k: v for k, v in values.items() if k in allowed})

10.3 Input validation
---------------------

``assert`` is stripped under ``python -O``. Any validation guarding
security-sensitive logic uses ``if`` / ``raise`` ``[review]``; ``ruff``'s ``S101``
is disabled, because Odoo uses ``assert`` for ORM invariants, so the linter will
not catch a security ``assert``.

.. code-block:: python

   if access_mode not in ("read", "write", "create", "unlink"):
       raise ValueError(f"Invalid access mode: {access_mode!r}")

10.4 SQL injection
------------------

**All dynamic SQL uses parameters or the ``SQL`` wrapper** ``[test_lint E8501]``.
f-strings, ``.format()`` and ``%`` on a query string are violations even when the
value comes from ORM metadata such as ``_table`` or ``field.name``.

.. code-block:: python

   from odoo.tools import SQL

   self.env.cr.execute("SELECT id FROM res_partner WHERE name = %s", (name,))

   self.env.cr.execute(SQL(
       "SELECT id FROM %s WHERE %s = %s",
       SQL.identifier(model._table),
       SQL.identifier(field.name),
       value,
   ))

``ruff``'s ``S608`` is disabled because the ORM legitimately builds SQL through
the ``SQL()`` wrapper. The ``test_lint`` checker covers this: it tracks constant
propagation across assignments and function boundaries, and treats
underscore-prefixed attributes such as ``self._table`` as trusted.

10.5 Related fields and ACLs
----------------------------

**Related fields default to ``compute_sudo=True``**, so a related field traversing
into a sensitive model is read as superuser and **bypasses the reader's ACLs and
record rules**. (Plain computed fields default to ``compute_sudo = store`` -- sudo
only when stored.) Do not reason from the field type; pick one of:

* set ``compute_sudo=False`` explicitly on that field, or
* restrict it with ``groups="..."``, or
* replace the related field with an explicit, ACL-respecting compute.

**A ``_search`` override that narrows what a user sees declares
``_search_visibility_fields``** ``[review]`` -- the tuple of field names the
override reads to decide visibility (``ir.attachment``: ``res_model``,
``res_id``, ``res_field``, ``public``, ``create_uid``). The ORM keeps one x2many
cache slot per access scope and evicts a user's slots on the model's records
when a write touches a field the user's read rule tests; a rule written in
Python is invisible to it, so the override names its fields. An override that
declares nothing is read as "every field", which is correct and costs a
refetch on every write to the model. ``base/tests/test_x2many_cache_scope.py``
checks each declared name is a field.

10.6 Controllers
----------------

* ``auth="public"`` runs as the Public user -- unauthenticated visitors reach it.
  Validate and sanitise every parameter, schema-validate the payload, and
  rate-limit the endpoint.
* ``auth="none"`` means no database access; it is mainly for framework use.
* ``auth="bearer"`` tokens must be scoped and validated, and never logged.
* Use ``Markup()`` for intentional HTML and escape user content. Never interpolate
  user input into ``Markup()`` with an f-string -- that is an XSS hole.
* Do not set ``csrf=False`` on a ``type="http"`` POST route without a written
  justification. ``jsonrpc`` is CSRF-exempt by design.

10.7 Constraints run privileged
-------------------------------

**A deliberate fork deviation.** ``@api.constrains`` methods run as ``sudo()`` by
default, like stored computed fields. Consequences:

* Reads inside a constraint never raise ``AccessError``, and any write it performs
  executes privileged -- hold constraint bodies to the same discipline as explicit
  ``sudo()`` code (§10.2).
* Opt back into user-aware validation with ``@api.constrains(..., sudo=False)``
  when the check must see the current user's view of the data.
* A callable spec (``@api.constrains(lambda self: ...)``) is resolved once per
  registry class and memoised, so an env-dependent field list is frozen at its
  first evaluation.

10.8 Access control
-------------------

Every new model ships explicit access rules ``[review]``. A model with no
``ir.model.access`` line is inaccessible -- or worse, silently admin-only.

* **ACLs** are table-level, in ``security/ir.model.access.csv``: one line per
  (model, group) with ``perm_read,perm_write,perm_create,perm_unlink``. Grant the
  minimum -- typically ``1,1,1,0`` for a user group and ``1,1,1,1`` for a manager
  group. Avoid group-less global lines.
* **Record rules** (``ir.rule``) are row-level: use them when access depends on
  the record's data -- owner, company, state. A rule with no groups applies to
  everyone and is AND-ed with every other rule. A rule with groups is
  ``composition="grant"`` by default: its domain is OR-ed with every other grant
  rule the user matches, so it can only ever widen access -- a grant rule cannot
  restrict, and adding one to a model silently disarms every other grant rule's
  restriction for the same group. A rule that must *narrow* what a group may reach
  declares ``composition="restrict"``: its domain is AND-ed like a global rule,
  but only for the group's members, and no grant rule can widen it. Say which
  modes it narrows with ``perm_*``; a rule with all four set governs creation
  too, including records the ORM creates on the user's behalf.
* **Multi-company** rules use ``[("company_id", "in", company_ids + [False])]`` so
  company-less shared records stay visible. Pair with ``check_company=True`` on
  relational fields (§2.9.10).
* Restrict sensitive **fields** with ``groups="module.group_xxx"`` -- enforced on
  both read and write, and the field is absent from every view for anyone outside
  the spec.
* **A field that everyone reads and only some may change carries**
  ``write_groups=`` ``[review]``, never a computed boolean feeding
  ``readonly="not flag"`` in the arch. The latter enforces nothing -- ``readonly``
  is a rendering hint, and the group it names is bypassed by ``web_save``, by
  import and by any RPC client. ``write_groups`` takes the same spec grammar as
  ``groups`` (including ``!`` and ``fields.NO_ACCESS``), or a callable receiving
  the recordset being written; it raises on ``write`` and ``create`` and makes
  ``fields_get`` report the field readonly, so no arch change is needed. **Delete
  the node's ``readonly`` attribute when converting one** -- an explicit
  ``readonly`` in the arch replaces the server's verdict instead of combining with
  it.
* **Gate a decision, not a structural attribute** ``[review]``. ``write_groups``
  refuses ``create`` as well as ``write``, and ``create`` checks ``default_*``
  context keys too, so a field every creator must supply -- a price, a category,
  a type, a company -- stops ordinary object creation the moment it is gated,
  including from a view whose action merely *defaults* it. A field whose value is
  a *decision* reserved to a group -- a cost, a published flag, a customer flag --
  is the case this is for; leave the rest a view-level ``readonly``.
* **Spell a group reference so it resolves** ``[test_lint test_group_refs]``. An
  external id no group answers to is not an error at runtime: ``_has_group``
  reads it as "not a member", so ``groups="module.group_typo"`` hides the node
  from everyone and ``groups="!module.group_typo"`` shows it to everyone, in
  silence. The gate holds this at zero over the checkout's own modules and leaves
  a reference into a module this checkout does not carry alone -- that is the
  optional-dependency idiom.

* **A read-only tier is the lowest rung of its privilege**
  ``[readonly_tiers]``. ``account``, ``stock``, ``sale``, ``purchase`` and
  ``mrp`` each carry ``group_<app>_readonly``: sequence 5 or 10, ``privilege_id``
  set, implying ``base.group_user``. It reads every model the app shows and
  writes none (``grants_write``); where a rung of the same privilege narrows a
  model by record rule, the tier carries a read rule stating its own scope
  (``ruleless``), usually ``[(1, '=', 1)]`` or the rung's type clause without
  its ownership clause; and no row duplicates a read ``base.group_user`` already
  holds through the row's own dependency closure (``dead_rows``). Record rules
  OR across a user's groups, so **the rung that implies the tier is the lowest
  one that already sees every document** -- "All Documents" in sales and
  purchase, User in stock and mrp, Invoicing in account -- and a gate on an
  affordance the tier must reach spells the pair
  ``groups="<transacting rung>,<tier>"``. A sixth app copies the rule, not a
  module.

10.9 Configuration and secrets
------------------------------

* **No hard-coded URLs, credentials or endpoints.** Use ``ir.config_parameter``,
  environment variables, or ``odoo.conf``.
* **Namespace** config keys as ``<module>.<setting>``; read them with
  ``self.env["ir.config_parameter"].sudo().get_param(key, default)``.
* ``ir.config_parameter`` values are readable by ``base.group_system``. For true
  secrets -- API keys, tokens -- prefer environment variables or ``odoo.conf``
  over the database.
* External dependencies are declared in ``__manifest__.py`` *and* pinned in
  ``requirements.txt`` (§1.2).

10.10 Deployment checklist
--------------------------

* ``--dev`` disabled; ``list_db = False``; ``admin_passwd`` changed from the
  default.
* ``proxy_mode = True`` behind a reverse proxy, with ``http_interface`` bound to
  localhost so only the proxy is public.
* ``dbfilter`` set; ``server_wide_modules`` minimal (the 19.0 default is
  ``base,rpc,web``).
* ``workers > 0``, with ``limit_time_cpu`` / ``limit_time_real`` /
  ``limit_memory_soft`` / ``limit_memory_hard`` / ``limit_request`` tuned.
* ``db_sslmode = require`` or ``verify-full`` -- the default ``prefer`` does
  **not** enforce TLS to PostgreSQL.
* ``gevent_port`` set for websockets and longpolling (``longpolling_port`` was
  removed); ``x_sendfile = True`` behind nginx or Apache; ``data_dir`` on a
  persistent, backed-up volume.
* Python dependencies pinned with hashes; ``pip-audit`` run regularly.

----

11. Performance
===============

11.1 N+1 queries
----------------

A ``search()``, ``search_count()``, ``search_fetch()`` or ``_read_group()`` call
inside a ``for`` loop over a recordset is a violation ``[test_lint E8507]``. The
rule is a hard zero: the 295 sites it reported on 2026-09-12 were each read, 40
were hoisted and the rest carry ``# noqa: E8507 - <why>``. The rule is
syntactic -- it sees the loop, not what the loop is over -- so a loop that runs
one query per *distinct key* is not an N+1 and is waived with the key named:
one query per company, per model, per timezone, per merged domain (records
sharing a domain were grouped before the loop), or a transient wizard that is
a single record. A loop over the records themselves is hoisted, never waived.

Aggregate outside the loop and index the result:

.. code-block:: python

   groups = self.env["child.model"]._read_group(
       [("parent_id", "in", records.ids)],
       groupby=["parent_id"],
       aggregates=["__count"],
   )
   count_map = {parent.id: count for parent, count in groups}
   for record in records:
       record.child_count = count_map.get(record.id, 0)

The same shape replaces nested loops:

.. code-block:: python

   lines_by_order = defaultdict(list)
   for line in all_lines:
       lines_by_order[line.order_id.id].append(line)
   for order in orders:
       for line in lines_by_order[order.id]:
           ...

11.2 Batching and aggregation
-----------------------------

.. list-table::
   :header-rows: 1

   * - Need
     - Use
     - Not
   * - Count
     - ``search_count(domain)``
     - ``len(search(domain))``
   * - Count an x2many
     - ``fields.Count("line_ids")``
     - a compute that spells ``len(record.line_ids)``
   * - Existence
     - ``bool(search(domain, limit=1))``
     - ``search_count(domain) > 0``
   * - Aggregate
     - ``_read_group(domain, aggregates=["x:sum"])``
     - ``sum(r.x for r in search(...))``
   * - Create many
     - ``create([vals1, vals2, ...])``
     - ``create(vals)`` in a loop
   * - Update many
     - ``write()`` on the whole recordset
     - iterate and write per record
   * - Load and read
     - ``search_fetch(domain, fields, limit=...)``
     - ``search(...)`` then attribute access
   * - Dicts, not records
     - ``search_read()``
     - ``search()`` + ``read()``

``search()`` instantiates every match in Python; ``search_count()`` is a
``SELECT COUNT(*)``. For aggregation, note the double unpack -- a group-less
``_read_group`` returns ``[(value,)]``:

.. code-block:: python

   [[total]] = self.env["account.move.line"]._read_group(domain, aggregates=["amount:sum"])

``search_fetch()`` returns a real recordset with the named fields pre-loaded,
unlike ``search_read()``, which returns dicts.

``len(record.line_ids)`` is the counting mistake that does not look like one: it
costs one query, not N, so it reads as batched, but ``One2many.read`` runs a
``search_fetch`` over the whole prefetch set and instantiates every line. On a
list-view page it is the slowest of the three, ``search_count()`` in a loop
included. **Do not convert one to ``_read_group`` by hand** -- on a form view,
where the lines have been read anyway, ``len()`` is the fastest of the three, and
a new record's lines are in cache and in no table. ``fields.Count("line_ids")``
takes that branch per call.

Iterating a recordset prefetches for the whole set, which is usually what you
want. For a large set processed one record at a time, ``with_prefetch([])`` stops
the ORM pulling every sibling's fields into memory.

11.3 ``ormcache``
-----------------

Use ``@ormcache`` for read-heavy, rarely-changing data: model metadata, parsed
views, ACL lookups, configuration values.

.. code-block:: python

   from odoo.tools import ormcache

   @ormcache("self.env.uid", "model_name")
   def _get_access_rights(self, model_name):
       """Return an access-rights mapping. Must not return recordsets."""
       ...

**Cached methods must never return recordsets.** The cursor that built the
recordset is closed by the time of a later call, and the result raises
``InterfaceError``. Return plain Python values.

The ORM invalidates automatically through ``modified()``;
``self.env.registry.clear_cache()`` clears everything.

11.4 Computed fields
--------------------

* ``store=True`` only when the field is searched, ordered or grouped on.
  Non-stored computes avoid recomputation on every write.
* **Every sub-field the body reads must appear in ``@api.depends``** ``[review]``.
  Incomplete chains cause silent stale data: if the method reads
  ``record.partner_id.country_id``, then ``"partner_id.country_id"`` must be
  listed -- ``"partner_id"`` alone is not enough.

  .. code-block:: python

     @api.depends("partner_id.country_id")
     def _compute_country(self):
         for rec in self:
             rec.country_id = rec.partner_id.country_id

* **Exception -- initialisation-only computes.** When a
  ``store=True, readonly=False`` compute exists to seed an initial value, a coarse
  ``"parent_id"`` dependency is deliberate: the precise ``"parent_id.lang"`` would
  recompute and overwrite the user's edit whenever the parent changed. Fields
  whose ``inverse`` writes back along the same path need the same coarsening to
  avoid a trigger cycle.
* Avoid long chains of stored computes depending on each other; flatten where you
  can.

11.5 Indexing
-------------

* ``index=True`` on fields used in search domains, ``ORDER BY`` or ``GROUP BY``.
* **The stored inverse Many2one of a One2many must be indexed**
  ``[test_lint test_index]``. Without it, every traversal of the One2many is a
  sequential scan of the child table. Genuine exceptions go in the checker's
  allow-list with a reason, not into a bare ``index=False``.
* Every index costs write and create time -- beyond the rule above, index
  selectively, driven by measurement.
* ``models.Index()`` takes a raw definition, which is how composite, partial and
  expression indexes are declared:

  .. code-block:: python

     _account_date_idx = models.Index("(account_id, date)")
     _state_date_idx = models.Index("(date_order) WHERE state != 'done'")
     _name_upper_idx = models.Index("(UPPER(name))")

* A **partial** index is the right default where queries always filter on a state.
  An **expression** index avoids a full scan for case-insensitive lookups. Other
  access methods are available through the same raw form -- ``USING gin`` is in
  use in the tree, and ``USING brin`` suits append-only time-series tables.
  Neither is a default; justify one with a query plan.

11.6 Raw SQL
------------

Any raw ``cr.execute()`` added in a PR ships ``EXPLAIN ANALYZE`` output in the
description, showing the plan uses the indexes you expect ``[review]``.

The ORM defers writes, so bracket raw SQL accordingly:

.. code-block:: python

   self.flush_model()          # push pending values to the database
   self.env.cr.execute(...)
   self.invalidate_model()     # drop the cache after writing behind the ORM's back

**An expression that carries a parameter and appears twice is two expressions**
``[review]``. psycopg 3 binds server-side, so each ``%s`` reaches PostgreSQL as its
own ``$N``. When the same SQL object is interpolated into the SELECT list and into
GROUP BY, the server sees ``"tag"."name"->>$2`` and ``->>$4``, and it refuses the
query with ``GroupingError: column ... must appear in the GROUP BY clause`` whatever
the values. psycopg2 inlined parameters, so upstream code of this shape worked. A
translated field is the usual carrier, because ``_field_to_sql`` renders it with the
language as a parameter; a company-dependent field inlines its company key and is
safe. Repeat such an expression only after ``.inlined(self.env.cr)``, or group by
the raw column or the select alias. ``l10n_ph_reports`` and ``l10n_vn_reports`` were
red on this until enterprise ``669855605fa``.

11.7 Cron batching
------------------

Scheduled actions over large recordsets batch with progress reporting. Do **not**
call ``cr.commit()`` -- ``_commit_progress`` commits for you and tells you how
much time is left.

.. code-block:: python

   from itertools import batched

   def _cron_process_orders(self):
       orders = self.env["sale.order"].search([("state", "=", "pending")])
       commit_progress = self.env["ir.cron"]._commit_progress
       commit_progress(0, remaining=len(orders))          # set the total once
       for batch_ids in batched(orders.ids, 100):
           orders.browse(batch_ids)._process()
           time_left = commit_progress(processed=100)     # framework decrements remaining
           if not time_left:                              # budget exhausted; it reschedules
               break

* Batch 100--1000 records to bound memory and lock duration. ``split_every`` is
  deprecated; use ``itertools.batched``.
* ``_commit_progress(processed=0, *, remaining=None, deactivate=False)`` --
  ``remaining`` is **keyword-only**. It returns the **remaining cron time in
  seconds** (``inf`` outside a cron, ``0`` at the deadline), not a record count.
  Set ``remaining`` once; afterwards pass only ``processed``.
* Pass ``deactivate=True`` on the final call of a one-shot cron.

11.8 Locking
------------

.. code-block:: python

   # fail immediately if another transaction holds the lock
   self.env.cr.execute(SQL(
       "SELECT id FROM %s WHERE id = %s FOR UPDATE NOWAIT",
       SQL.identifier(self._table), self.id,
   ))

   # skip locked rows — job queues, cron dispatch
   self.env.cr.execute(SQL(
       "SELECT id FROM %s WHERE state = %s FOR UPDATE SKIP LOCKED",
       SQL.identifier(self._table), "pending",
   ))

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Mode
     - Use for
   * - ``FOR UPDATE NOWAIT``
     - critical sections -- sequences, payment processing. Raises
       ``OperationalError`` when locked; always handle it.
   * - ``FOR UPDATE SKIP LOCKED``
     - job queues and cron dispatch; silently skips locked rows
   * - ``FOR NO KEY UPDATE``
     - updates that do not touch foreign-key columns

Lock, operate and commit as fast as possible. Prefer an ORM ``search()`` with a
domain over a table-level lock.

----

12. Migration Scripts
=====================

12.1 Layout
-----------

.. code-block::

   migrations/
     1.1.0/
       pre-migrate.py
       post-migrate.py

The directory name is the module ``version`` in ``__manifest__.py`` that
introduces the change, **with the series prefix §1.2 requires there stripped**
-- a manifest at ``19.0.1.2.0`` gets a directory ``1.2.0``, never
``19.0.1.2.0`` [test_lint lint_migration_series_prefix]. Odoo prefixes a bare
version with the server major at load time, so the two spellings name the same
version and, inside one series, select the same scripts. They diverge across one:
``_is_migration_applicable`` compares only the tail of the installed version for
a bare directory and the absolute version for a prefixed one, so on a database
carrying ``18.0.1.30`` a folder ``1.8`` is correctly skipped and ``19.0.1.8``
runs again. Several bundled directories carry pre-19.0 module versions for
exactly that comparison, which is why the prefix is the form this tree refuses
rather than the form it requires.

A directory pinned to an **older** series (``15.0.5.0``) is a different thing
and stays: it names an absolute version on a multi-series upgrade path. A name
that matches neither shape is skipped by the loader with a log line nobody
reads [test_lint lint_migration_version_unreadable].

The special ``0.0.0`` directory runs on **every** update: first in the ``pre``
stage, last in ``post`` and ``end``.

Scripts are matched on the **stage prefix alone** -- ``name.startswith("pre-")`` /
``"post-"`` / ``"end-"`` -- so any suffix runs, ``-migrate.py`` and
``-migration.py`` included, and a descriptive name such as
``post-migrate_update_taxes.py`` is fine. Within a stage they run in filename
order.

The ``migrate`` function's signature is checked and must be exactly two positional
parameters named ``(cr, version)`` -- ``_cr`` / ``_version`` are the only accepted
aliases. Anything else raises ``TypeError`` at migration time, when the upgrade is
already running.

Lint rules are relaxed under ``**/migrations/**`` -- ``E501``, ``UP``, ``PTH`` and
``ERA`` are suppressed, because migration scripts are raw SQL, legacy patterns and
commented reference code by nature.

12.2 Writing one
----------------

.. list-table::
   :header-rows: 1
   :widths: 20 14 66

   * - Script
     - ORM
     - Use for
   * - ``pre-migrate.py``
     - no
     - renaming columns and preventing data loss before the ORM recreates them
   * - ``post-migrate.py``
     - yes
     - data transformation and field-value migration
   * - ``end-migrate.py``
     - yes
     - cross-module cleanup after every module is processed

.. code-block:: python

   def migrate(cr, version):
       if not version:
           return
       ...

The framework passes a **cursor**, not an environment. Guard ``pre-migrate`` SQL
with the helpers in ``odoo.db.schema`` -- ``table_exists``, ``column_exists``,
``index_exists``, ``create_column``, ``convert_column``, ``drop_columns``,
``drop_constraint`` --
rather than hand-written ``information_schema`` queries. (There is no
``odoo.tools.sql`` in this fork.) ``openupgradelib`` is available but is not the
house default.

**Removing a stored field: its column is dropped in the same upgrade, and
post-migrate is the last place its values can be read** ``[review]``. Odoo deletes
the ``ir.model.fields`` row for a field the code no longer declares and issues
``ALTER TABLE ... DROP COLUMN CASCADE`` for it, from ``ir.model.data._process_end``
-- which ``modules/loading.py`` runs *after* every ``post-migrate``. So a
``post-migrate`` that harvests the old values into their new home works, and there
is nothing left for a later version to harvest.

**A field that stops being stored keeps its column until a migration drops it**
``[review]``. The row in ``ir.model.fields`` survives -- the field is still
declared -- so ``_process_end`` has nothing to delete, and the ORM creates
columns but never drops one: a ``related=`` that loses ``store=True`` (§2.3,
``E8529``) leaves the column, its index and any constraint over it in place,
read by nothing and written by no one. The same change ships a
``post-migrate`` calling ``schema.drop_columns(cr, table, columns)`` -- one
``ALTER TABLE`` for the table, since each takes an exclusive lock. It cascades:
a report view selecting the column is taken down, logged by name, and rebuilt by
its model's ``init()`` later in the same upgrade.

**A Many2many is the exception: its relation table is never dropped**
``[review]``. ``_drop_m2m_tables`` skips any field whose ``state`` is not
``manual``, and a field declared in Python is ``base``. Removing a code-defined
Many2many deletes its ``ir_model_fields`` row and leaves the join table, its rows
and its foreign keys in place for good. Useful -- the old configuration stays
readable -- but not cleanup: drop the table yourself if the data is not worth
keeping, and say so in the script.

**Do not plan that harvest across two versions** ``[review]``. ``migrate_module``
runs **every** ``pre`` script for every version in range before **any** ``post``
script, so a ``pre-migrate`` at a *higher* version still executes before a *lower*
version's ``post-migrate``. Splitting "copy the values" and "drop the column"
across two versions therefore drops first and copies nothing -- and the data is
gone with no error, because dropping a column the ORM was going to drop anyway
raises nothing. Copy and link in one ``post-migrate``.

12.3 When one is required
-------------------------

**Required**: adding or removing a required field on an existing model; changing a
field's type; renaming a model or field; any non-trivial data transformation.

**Not required**: adding an optional field; installing a new module; view-only
changes; adding or removing a Many2many relation.

12.4 What a migration cannot reach
----------------------------------

**No migration phase runs late enough to see rows a model discovers from the
registry.** In ``odoo/modules/loading.py``, ``run_end_migrations()`` is called
before ``register_model_hooks()``, and a post-migration runs earlier still, while
the modules that declare what is being discovered are not yet loaded. A migration
written to fix up such rows therefore matches nothing, writes nothing and raises
nothing — it reports success having done its work against an empty set. [review]

This is §2.4.14's failure one level up: a binding no import graph reaches, and a
migration no registry reaches, both report success having done their work against an
empty set. Neither has a gate; both are caught by asking what the thing matched.

Do it in the hook that produces the rows instead: ``_register_hook`` runs on every
registry load, after every module is in, and is the only place that sees the whole
declaration. A row it creates is a fact about the code, so it is derived rather than
migrated, and a value carried over from a legacy parameter is carried there too.

Corollary, for a hook that queries its own model: guard it with
``table_exists(self.env.cr, self._table)``. The hook runs on every load, including
the load of a database whose module predates the table, and the upgrade that would
create the table has not run yet — without the guard that database cannot boot at
all, not even to be upgraded.

----

Appendix A — Fork field renames
================================

``project.task`` renames fields in this fork. Reading, searching or sorting on a
vanilla name raises, surfacing as a 500 over JSON-RPC and MCP. Apply these
regardless of what training data suggests.

.. list-table::
   :header-rows: 1

   * - Vanilla Odoo
     - This fork
   * - ``stage_id``
     - ``step_id`` (Many2one → ``project.workflow.step``)
   * - ``date_deadline``
     - ``date_end``
   * - ``date_last_stage_update``
     - ``date_last_status_change``
   * - ``personal_stage_type_id``
     - ``personal_triage_id`` (Many2one → ``project.task.triage``). Note the
       separate related field ``triage_id`` → ``project.triage``.
   * - ``depend_on_ids``
     - ``predecessor_ids``
   * - ``dependent_ids``
     - ``successor_ids``
   * - ``planned_date_begin``
     - ``date_start``, so the planned window is the ``date_start`` / ``date_end``
       pair every other model in the family already spells that way
   * - ``planned_date_start``
     - ``date_start_effective`` -- computed, unstored, and NOT the start date. It
       falls back to ``date_end`` when ``date_start`` is unset, which is what the
       old name hid by differing from ``planned_date_begin`` in one word.

So ``("stage_id.fold", "=", False)`` becomes ``("step_id.fold", "=", False)``, and
``order="date_deadline asc"`` becomes ``order="date_end asc"``.

The rest of the project family moves onto the same ``date_`` / ``is_`` / ``amount_``
spellings §2.3 prescribes:

.. list-table::
   :header-rows: 1

   * - Model
     - Vanilla Odoo
     - This fork
   * - ``project.milestone``
     - ``deadline``
     - ``date_deadline``
   * - ``project.milestone``
     - ``reached_date``
     - ``date_reached``
   * - ``project.workflow.step``
     - ``rating_request_deadline``
     - ``date_rating_request``
   * - ``project.project``
     - ``analytic_account_balance``
     - ``amount_analytic_balance``

**``date_deadline`` is now a fork name on one model and a vanilla name on
another, and they point opposite ways.** On ``project.task`` it is the *vanilla*
spelling and raises -- the fork calls that field ``date_end``. On
``project.milestone`` it is the *fork* spelling and is correct. The search filter
``<filter name="deadline">`` on ``project.task`` is a third thing again: a filter
name grouping by ``date_end``, inherited by name from ``industry_fsm``, and it
does not move.

These models are the fork's own and were never vanilla, so they are recorded here
only to keep one list: ``project.task`` gained ``cpm_date_earliest_start`` and
``cpm_date_latest_start`` (from ``earliest_start`` / ``latest_start``, which sat
beside ``cpm_date_start`` and ``cpm_date_end`` without the prefix that says they
are critical-path output); ``project.baseline.line`` ``date_planned_start`` /
``date_planned_end``; ``project.benefit`` ``date_review`` /
``date_review_reminder``; ``project.gate`` ``date_review``;
``project.gate.criterion`` ``is_met``; ``project.retrospective.action``
``date_due``; and ``project.project`` ``date_premortem`` and
``premortem_participant_ids``.

``purchase.order`` and ``purchase.order.line`` rename one field, so the date a
human committed to has a single name across order types:

.. list-table::
   :header-rows: 1

   * - Vanilla Odoo
     - This fork
   * - ``date_planned``
     - ``date_commitment``

``sale.order.date_commitment`` already carried that meaning, so shared code in
``base_order`` now names it once: ``mixin.order``'s ``is_late`` domain reads
``date_commitment`` on both.

**``date_planned`` still exists, and still means something else**: a *derived,
unstored* estimate on ``sale.order`` (and on ``sale.order.line`` under
``sale_stock``), the scheduling date on ``stock.move`` and ``stock.picking``, the
key in the procurement ``values`` dicts, and a field on the replenishment wizard.
None of those were renamed.

``sale.order`` and ``pos.order`` spelled the link to ``stock.reference``
``stock_reference_ids`` while ``stock.move``, ``stock.picking``, ``purchase.order``,
``mrp.production`` and ``repair.repair`` all spelled it ``reference_ids``. The two
outliers moved, so the concept has one name. The relation tables did not:
``stock_reference_sale_rel`` and ``stock_reference_pos_order_rel`` keep their names
and columns, so this Many2many rename carries no column migration -- only stored
expressions, rewritten per model by ``sale_stock`` 1.3 and ``point_of_sale`` 1.0.6.

``res.partner``: the phone scalars became a related model
----------------------------------------------------------

``res.partner`` has **no** ``phone`` and no ``mobile`` field in this fork. Both
Char columns were replaced by ``phone.number``, a model of its own carrying the
number, a ``type`` out of mobile / landline / fax / whatsapp / emergency, a
country, a label and a primary flag, related through a Many2many.

.. list-table::
   :header-rows: 1

   * - Vanilla Odoo
     - This fork
   * - ``phone``
     - ``phone_ids`` (Many2many → ``phone.number``); ``main_phone_id`` is the
       computed first active Landline, ``main_mobile_id`` the first active Mobile
   * - ``mobile``
     - the same ``phone_ids``, with ``type`` set to ``mobile``

So ``partner.write({"phone": "555-0100"})`` raises ``ValueError: Invalid field
'phone' in 'res.partner'`` rather than failing a comparison, because
``_write_check_field_access`` resolves every key in ``vals`` before any of them is
written. A read of ``partner.phone`` raises ``AttributeError`` the same way.
Create one with ``Command.create({"number": ..., "type": "mobile"})`` on
``phone_ids``; read the display number from ``main_mobile_id.number`` or
``main_phone_id.number``.

**A field this ordinary goes stale silently in fixtures.** Two marin suites wrote
``phone`` on a partner for months -- one in a ``create``, one in a ``write`` --
and `partner_group_restricted` had already followed the rename in its editable
whitelist, which is the tell that the module was updated and its tests were not.
Neither is a phone defect; both are this appendix's absence.

``res.partner``: the two manufacturer flags
--------------------------------------------

Neither name was ever vanilla. Both arrived with ``product_manufacturer``, an OCA
port that carried them under the OCA original's spellings, and both were renamed
onto §2.3 when that module was dissolved into ``product``. They are recorded here
because code written against ``product_manufacturer`` -- or against the OCA
module it came from -- uses the old ones.

.. list-table::
   :header-rows: 1

   * - ``product_manufacturer``
     - This fork
   * - ``manufacturer``
     - ``is_manufacturer`` (Boolean). The label stays ``Manufacturer``, so the
       rename is invisible in the UI and in every catalogue
   * - ``product_count``
     - ``count_manufactured_products`` -- a ``fields.Count`` over
       ``manufactured_product_ids``, computed and unstored, so it has no column.
       The old name also collided in meaning with ``product.category.product_count``
       in the same module

So ``partner.manufacturer`` raises, and a view domain reading
``[('manufacturer', '=', True)]`` on ``res.partner`` raises when the dropdown or
action is opened rather than when the view loads. Three other models keep a
``manufacturer`` field of their own and are untouched: ``iot.device``,
``remote.config`` and, as a plain Char, nothing else.

**``count_manufactured_products`` is deliberately against the grain of the tree.**
§2.3's table prescribes the ``count_`` prefix, and the tree does not follow it:
477 field declarations end in ``_count`` against 48 that begin with ``count_``,
measured over ``odoo/addons`` and ``odoo/odoo/addons`` excluding tests. A new name
landing with a fold is the cheap moment to be canonical; a mass rename of an
existing family in one module is not, and is why ``project``'s counters were left
alone.

Order lines: ``product_qty`` and ``product_uom_qty`` swapped meanings
---------------------------------------------------------------------

Both names still exist on ``sale.order.line`` and ``purchase.order.line``, and
both carry the *other* one's upstream meaning. ``mixin.order.line.amount``
(``addons/base_order/models/mixin_order_line_amount.py``) defines them:

.. list-table::
   :header-rows: 1

   * - Field
     - This fork
     - Upstream
   * - ``product_qty``
     - the ordered quantity, **in the line's own unit** (``product_uom_id``).
       Computed with ``readonly=False`` — this is the one to write.
     - the ordered quantity converted to the product's reference unit
   * - ``product_uom_qty``
     - the same quantity converted to the product's **reference** unit
       (``product_id.uom_id``). Computed, stored, ``readonly=True``.
     - the ordered quantity in the line's own unit

**Writing ``product_uom_qty`` raises.**
``mixin.order.line.amount._check_write_derived_quantity`` refuses it, from
``create`` and from ``write`` alike, with ``product_uom_qty is computed from
product_qty and cannot be written; set product_qty instead``.

That is a change of kind, and this appendix described the old one until
2026-09-07. Before ``fed310f743c`` the write was **silent**: in ``create`` the
value was discarded and ``product_qty`` fell back to its default of 1, so a
test that ordered 10 ordered 1 and usually still passed; in ``write`` it landed
in the stored column while ``product_qty`` kept its old value. Read any
pre-September reasoning about this pair with that in mind — a site the old text
called inert is a hard failure now.

So: **write ``product_qty``**, and read it wherever the quantity is about to be
converted from ``product_uom_id`` or compared with a BoM's ``product_qty``. Read
``product_uom_qty`` only where the reference unit is the point -- comparing a
line against free stock. ``stock.move.product_uom_qty`` is unrelated and
unchanged: a real, writable field there.

Counted by ``order_line_qty.py`` (removed with ``tooling/`` on 2026-09-11) and
ratcheted as ``orderlineqty``, which was floored at 31 while the write was silent and driven
down module by module. The raise arrived first, so every remaining site was a
red test rather than drift, and the floor went to **zero** in one sweep: **33**
writes across 21 test files, every one a fixture building an order line, none of
them a place where the reference unit was the point.

Thirty-three against a floor of thirty-one, and **both of the extra two were
sites the gate could not see** — each found by a suite failing, not by the scan:

- ``order.line_ids = [Command.create({...})]``. The assignment branch only read
  ``<order line>.product_uom_qty = value``, so a command list assigned straight
  to the one2many was invisible although it reaches exactly the rows a
  ``write`` of the same list reaches. Closed, and pinned by
  ``test_assigning_a_command_list_to_the_o2m_is_a_write`` beside its negative
  twin on ``picking.move_ids``, where the field is real.
- **A payload the call site named.** ``test_event_full``'s ``test_event_mail``
  assembled ``order_line_vals`` into a variable and passed it to ``write`` on
  the next line; the scan reads dict *literals*, so it saw nothing.
  Still open — resolving a name to its dict is local dataflow, not a shape
  test, and the false-positive question there has not been thought through.

A floor of zero is what makes the remaining gap survivable: with nothing banked,
the next literal site fails the gate on the day it lands, and only the named-dict
form can still arrive quietly.

``hr.expense`` moves its own review off the name ``mixin.approval`` gives the
approval request's state:

.. list-table::
   :header-rows: 1

   * - Model
     - Vanilla Odoo
     - This fork
   * - ``hr.expense``
     - ``approval_state``
     - ``review_state`` ("Review Status": submitted / approved / refused). Once
       the expense adopts the approval engine, ``approval_state`` is the approval
       request's state. The 2.3 migration rewrites saved views, filters, actions
       and export lines on ``hr.expense``, so none of them silently reads the
       other field.

``maintenance`` puts ``date_`` first on every date it owns and names what each
one dates. ``maintenance.plan`` is the fork's own, and ``date_order`` was an
earlier fork name for vanilla ``request_date``; both are listed so the list stays
one. The 1.7 migration renames the columns and rewrites stored expressions on each
model.

``date_order`` defaulted to the day the order was created and nothing wrote it again,
so it only repeated ``create_date`` as a date. ``date_confirmed`` is a datetime
stamped when the order leaves draft and cleared when it returns there, and
reliability counts its local day as the failure. The 1.7 migration takes it from
each order's first tracked state change, or from ``create_date`` when there is
none, and clears it on drafts.

``maintenance.order.owner_user_id`` is dropped: an order is requested by whoever
created it, ``create_uid``, as a sale, purchase or invoice is. It differed only
under ``hr_maintenance``, which filled it from ``employee_id``; that module is
retired by base 1.78, which drops ``employee_id`` and the implication that made
every HR officer a maintenance manager. Maintenance 1.7 rewrites stored
expressions naming ``owner_user_id`` to ``create_uid``.

.. list-table::
   :header-rows: 1

   * - Model
     - Previous name
     - This fork
   * - ``maintenance.order``
     - ``date_order`` (vanilla ``request_date``)
     - ``date_confirmed``
   * - ``maintenance.order``
     - ``close_date``
     - ``date_done``
   * - ``maintenance.order``
     - ``schedule_date`` / ``schedule_end``
     - ``date_scheduled_start`` / ``date_scheduled_end``
   * - ``maintenance.order``
     - ``date_occurrence``
     - ``date_plan_slot``
   * - ``maintenance.plan``
     - ``date_start`` / ``date_next``
     - ``date_first_occurrence`` / ``date_next_scheduled``
   * - ``resource.resource``, ``resource.asset``, ``mrp.workcenter``
     - ``date_effective`` (vanilla ``effective_date``)
     - ``date_in_service``
   * - ``resource.resource``, ``resource.asset``, ``mrp.workcenter``
     - ``latest_failure_date`` / ``estimated_next_failure``
     - ``date_last_failure`` / ``date_next_failure``
   * - ``team.team``
     - ``maintenance_todo_order_count_date``
     - ``maintenance_todo_order_count_scheduled``

Appendix B — References
========================

In this repo:

* ``ruff.toml`` -- linter and formatter configuration, with the rationale for
  every suppression
* ``odoo/addons/test_lint/`` -- the fork's own checkers
* ``odoo/addons/test_lint/tests/floors.json`` -- the committed ``test_lint`` floors
* ``pytest.ini`` -- the Tier 1 suite definition

In the knowledge repository's ``reference/``:

* ``odoo/odoo-19-development-context.md`` -- Odoo 17→19 API changes
* ``dev/error-catalog.md`` -- known PATH / CONFIG / SERVICE / POSTGRES errors
* ``owl/`` -- OWL hooks, stores and lifecycle
* ``python-pg/`` -- Python 3.14 and PostgreSQL 18 / psycopg 3 patterns

External:

* `Odoo 19 Coding Guidelines <https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html>`_
* `OCA CONTRIBUTING.rst <https://github.com/OCA/odoo-community.org/blob/master/website/Contribution/CONTRIBUTING.rst>`_
* `PEP 8 <https://peps.python.org/pep-0008/>`_

Appendix C — Retired patterns
==============================

Flag these on sight; migrate opportunistically when you are already editing the
file.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Retired
     - Replacement
   * - Suffix XML IDs (``sale_order_view_form``)
     - Prefix style (§3.2)
   * - Commit tags ``[MIG]``, ``[CLA]``
     - ``ADD`` / ``REF`` on the migration script; ``REF`` on the licence change
       (§7.1) -- both described the *subject*, not the intent
   * - Suffix mixin names, and abstract models that are mixins but carry no marker
     - Prefix ``mixin.`` (§2.2.1)
   * - Two model classes in one ``models/*.py``
     - One per file, named from ``_name`` (§1.3)
   * - Field ordering by type
     - Semantic blocks (§2.3)
   * - Method ordering by Spanish category
     - The section banners in §2.2
   * - Google-style docstrings (``Args:``, ``Returns:``)
     - Sphinx fields (§2.5)
   * - ``<tree>`` views and ``view_mode`` ``tree``
     - ``<list>`` (§3.3); core is fully migrated
   * - ``attrs=`` / ``states=``
     - Python expressions ``invisible=`` / ``readonly=`` / ``required=`` (§3.3)
   * - Renaming an inherited core method to fit §2.4
     - Override under the original name (§2.4)
   * - ``split_every``
     - ``itertools.batched`` (§11.7)
   * - ``with_context(force_company=...)``
     - ``with_company()`` (§2.6) -- the key is now ignored with only a
       ``DeprecationWarning``, so surviving call sites silently use the wrong
       company
   * - ``_sql_constraints = [...]``
     - ``models.Constraint`` (§2.9.8)
   * - ``def create(self, vals)``
     - ``@api.model_create_multi def create(self, vals_list)`` (§2.6)
   * - Magic x2many tuples ``(0, 0, {})``
     - ``Command.*`` (§2.9.7)
   * - ``name_get`` / ``_name_search``
     - ``_compute_display_name`` / ``_search_display_name`` (§2.4, §2.6)
   * - OCA ``queue_job``
     - ``ir.job`` and ``@api.job`` (§2.9.14)
   * - wkhtmltopdf workarounds; ``dpi`` / ``header_spacing`` /
       ``disable_shrinking`` on paperformats
     - WeasyPrint paged media (§3.6.1)
   * - ``_sanitize_*``
     - The row the body belongs to, per §2.4.20's table -- ``_normalize_`` when
       it reshapes a value, ``_filter_`` a subset, ``_update_`` an in-place
       mutation, ``_prepare_`` a payload, ``_check_`` when it raises. Reserved
       for HTML sanitisation and for a hook named after a ``sanitized_*`` field

Appendix D — Document history
==============================

One row per change, one clause. The argument lives in the section it moved.

.. list-table::
   :header-rows: 1
   :widths: 8 12 80

   * - Version
     - Date
     - Summary
   * - 6.59
     - 2026-09-20
     - ``company-field-outside-config`` is ``E8530``: it shared ``E8529`` with
       ``stored-related``, so one ``noqa`` named both and ``test_checkers``'
       shared-code test was red. A company's configuration is read under the
       reader's own access (record rule on ``company_id``, the link's search in
       the caller's scope), and a tenant's identity fields are written under the
       tenant's access.
   * - 6.58
     - 2026-09-20
     - §2.3: a boolean field attribute takes a Python bool; the ORM raises
       ``TypeError`` on ``store="True"`` instead of reading it as true.
   * - 6.57
     - 2026-09-19
     - ``stored-related`` is ``E8529``: it shared ``E8528`` with
       ``receiver-fail-open``, so one ``noqa`` named both. The ``E85xx`` range
       reads ``E8529``; ``test_checkers`` refuses a shared code.
   * - 6.56
     - 2026-09-19
     - §2.3: an ``@api.constrains`` naming a related field fires when its source
       changes, with or without a column; a constraint is no reason to store one.
   * - 6.55
     - 2026-09-18
     - §2.3: a related field is not stored to make it groupable (``E8528``,
       floored); a UNIQUE/EXCLUDE or a measured composite index keeps the copy,
       with a ``noqa`` naming it. The ``E85xx`` range reads ``E8528``. §12.2: a
       field that stops being stored keeps its column until a migration calls
       ``schema.drop_columns``.
   * - 6.54
     - 2026-09-16
     - §11.6: an expression with a bound parameter used twice (SELECT and GROUP BY)
       reaches the server as two expressions under psycopg 3; inline it first.
   * - 6.53
     - 2026-09-16
     - §2.4.1: a zero-argument ``_compute_`` assigning a field no model declares is
       dead and is deleted, not renamed; constructed dispatch counts as a binding.
   * - 6.52
     - 2026-09-16
     - §2.4.3: an accumulator — a body writing into a container its caller passes in
       and returning nothing — is the Addition row's ``_add_``; ``_fill_`` of a
       caller's container is abolished.
   * - 6.51
     - 2026-09-16
     - §2.4.18: the ingestion cycle gains an Acquire row before Identify —
       ``_download_`` for a document taken from a remote service, ``_import_``
       for local records made from what it returned, ``_get_`` for a remote
       answer that is not stored — retiring ``_fetch_`` of something remote.
   * - 6.50
     - 2026-09-16
     - §3.9: ``noupdate`` protects every write but the first. A module being
       installed loads its data with ``"init"``, which is the one mode
       ``convert.py`` does not skip, so the flag cannot protect a record the
       install writes -- including one a ``pre_init_hook`` handed the xml id to,
       which is how ``fleet``'s catalogue replaced four manufacturer logos on a
       production copy. The stored flag is never refreshed either
       (``_update_xmlids`` writes ``model`` and ``res_id`` only), so unfreezing a
       database takes a pre-migration, not a tree edit (agromarin ``f10b85a09`` /
       ``marin`` 19.0.1.71). §2.4.19 points here.
   * - 6.49
     - 2026-09-15
     - §2.4.1: "unbound" is a claim about a search — a binding hides behind a
       non-string ``default=``, a protocol namespace, or a data-derived tail. The
       signature settles the rest (a ``compute=`` passes nothing, so a definition
       taking arguments is not that hook), and a zero-argument survivor is left
       alone because renaming a field that lost its ``compute=`` makes the defect
       unfindable.
   * - 6.48
     - 2026-09-15
     - §12.4: no migration phase runs late enough to see rows a ``_register_hook``
       discovers from the registry, so such a migration reports success against an
       empty set; a hook querying its own model guards with ``table_exists``.
   * - 6.47
     - 2026-09-15
     - §2.4 head: thirty of its thirty-one gate markers name a tool deleted with
       ``odoo/tooling/``, so the section is review-held and its census table is a
       frozen reading -- 10 of 59 rows still true, 7 unre-derivable. §2.4.3 gains
       the measured limit of the redundancy claim; §2.4.4's first-token frequency
       heuristic is replaced by a grammar test; §2.4.5 reserves ``convert_to_*``;
       §2.4.20 abolishes ``_sanitize_``; §2.4.21 asks for a return annotation
       wherever the name makes a type claim; §2.1's length ratchet is gone.
   * - 6.46
     - 2026-09-14
     - §3.6.1: the PDF engine, ``report.layout``, the company document-layout
       fields and the two technical reports live in ``web``; ``base`` keeps the
       action type and the HTML and text renders.
   * - 6.45
     - 2026-09-12
     - §11.1: ``E8507`` is a hard zero; a loop that runs one query per
       distinct key is waived with the key named, a loop over the records is
       hoisted.
   * - 6.44
     - 2026-09-12
     - §3.1: the XML declaration is part of the canonical format the
       formatter writes; it is not part of a document's identity.
   * - 6.43
     - 2026-09-12
     - §3.7: menus are moved by ``_relocate_menus.py``; the menus file loads
       after the actions it names and before the first file that needs a menu;
       menu-binding records live with the menus. No XML rule is floored.
   * - 6.42
     - 2026-09-12
     - §3.6: ``t-esc`` is fixer-owned (``_modernize_output_directives.py``);
       no XML rule is floored any more.
   * - 6.41
     - 2026-09-12
     - §3.1: the x2many command tuples are fixer-owned
       (``_modernize_commands.py``) and the rule is a hard zero.
   * - 6.40
     - 2026-09-12
     - §3.1: the record field-order canon covers 22 technical models and is
       pinned to the registry; its four dead names (``groups_id``,
       ``print_wizard``, ``filter``, ``mobile_view_filter``) are gone.
   * - 6.39
     - 2026-09-12
     - §3: the static XML rules (``_xml_rules.py``, one ``lint_xml_*``
       ratchet each) named beside the conventions they hold; menus go in
       ``views/<module>_menus.xml``; ``t-out`` over ``t-esc``; every
       reference shape the loader resolves is checked statically.
   * - 6.38
     - 2026-09-12
     - §1.2: the manifest vocabulary is ``MANIFEST_KEY_ORDER`` alone, the
       fixer normalises (defaults dropped, whitespace, case, set bundles,
       unescaped strings) and the shape gate reads "would rewrite"; the
       value rules the fixer cannot decide are listed, and the two scripts
       run over the sibling repositories by hand.
   * - 6.37
     - 2026-09-12
     - §2.2.2: "every consumer already reaches it" is a manifest closure, run
       over who asks the question and not over who is folding today; the four
       recurrence mixins move from ``resource`` to ``base`` because ``ir.cron``
       asks it and a ``base`` -> ``resource`` edge is a cycle.
   * - 6.36
     - 2026-09-12
     - §2.2.2: a mixin may live with the module that owns its subject matter
       instead of in ``base``; ``mixin_recurrence`` is dissolved into
       ``resource`` rather than ``base``, which is where the iCalendar engine
       lifted out of ``calendar.recurrence`` joins it.
   * - 6.35
     - 2026-09-12
     - §1.2: a demo or data file never stores a secret -- a
       ``credential.credential`` exists unprovisioned until one is entered,
       so a module installs and loads its demo on a server with no
       ``ODOO_API_ENCRYPTION_KEY``.
   * - 6.34
     - 2026-09-12
     - §1.2: demo data reaches a workflow state through the workflow, and a
       demo file must load -- the ``--with-demo`` sweep that found twelve
       that did not; §6.2: a fixture reusing a shipped record states every
       setting it relies on, because demo may have reconfigured it.
   * - 6.33
     - 2026-09-11
     - Appendix A gains ``hr.expense.approval_state`` to ``review_state``: the
       expense keeps its own review while ``mixin.approval`` names the approval
       request's state ``approval_state``, and the migration rewrites stored
       references so a saved filter cannot silently switch fields.
   * - 6.32
     - 2026-09-11
     - §1.1, §1.3: the directory names are plural -- ``wizards/`` and
       ``reports/``, never ``wizard/`` or ``report/``; §1.2, §1.3: a demo file
       lives in ``demo/``, never ``data/``. The tree was converted in the same
       pass -- 510 directories renamed, 330 demo files moved -- so both rules
       are contracts, not partial adoption.
   * - 6.31
     - 2026-09-10
     - §6.7: an ``at_install`` suite of a module already installed beside its
       dependents is deferred by the loader until those dependents are loaded,
       because the partial registry cannot represent a table that carries their
       columns; a fresh install is unchanged.
   * - 6.30
     - 2026-09-09
     - §2.4.13: the shared gate governs every file under a manifest --
       controllers, tools, report, utils, migrations -- and ``SKIP_DIRS``
       spells ``_vendor``; §2.4.20's synonyms and the three assemble synonyms
       move from the core-only table into ``ABOLISHED``. Floors banked at the
       widened readings (159 / 275 / 116) as newly visible names, not new ones;
       ``locate`` and ``refresh`` argued out of the shared table.
   * - 6.29
     - 2026-09-09
     - §2.4.13: ``ADDON_HELPER_DIRS`` is ``{models, wizard, wizards}``, so an
       addon's ``controllers/`` fails both of the sibling gate's tests and has
       never been in any vocabulary gate's population -- 61 names in ``odoo``,
       23 in ``enterprise``, 26 in ``agromarin``, measured at four named commits
       and recorded as newly **visible** rather than new. Not landed as a
       widening, because three of those floors are hard zeros and §9.4 calls a
       sibling zero a contract; closed for ``addons/web`` instead by onboarding
       it to ``naming_core_vocabulary.py``, whose scan has no helper-dirs filter
       and therefore reads controllers for free. §2.4.19: the vocabulary stops
       at the language boundary -- 332 abolished-verb definitions in
       ``web/static/src``, most of them OWL, ``Map`` and factory contracts
       rather than defects -- so only body-discriminated rows transfer, and an
       OWL template is JavaScript's stored-Python binding.
   * - 6.28
     - 2026-09-09
     - Appendix A gains the two ``res.partner`` manufacturer flags, renamed onto
       §2.3 when ``product_manufacturer`` dissolved into ``product``:
       ``manufacturer`` to ``is_manufacturer`` and ``product_count`` to
       ``count_manufactured_products``. The second is against the tree's grain --
       477 ``_count`` suffixes to 48 ``count_`` prefixes -- and the entry says so,
       because the guideline is the tiebreak for a NEW name while a mass rename of
       an existing family is the move it does not license.
   * - 6.27
     - 2026-09-08
     - §2.4.2: ``selection=`` is a sixth field-declaration keyword and the §2.4
       Selection row was enforced by nothing. Closed as its own scope in
       ``field_hook_naming.py`` rather than by adding it to ``ATTRS``, because
       the Selection row names a hook for its **values** while every other rule
       in that file asserts the opposite -- through ``ATTRS`` it would have
       demanded a rename of the three declarations that correctly share one
       ``_selection_target_model``. It resolves the forwarding lambda as well as
       the string, and two of its findings were module-level functions passed by
       reference, which no scan over ``selection="_x"`` could ever have read --
       so the frozen figure behind it was the smaller half of the residue.
   * - 6.26
     - 2026-09-08
     - §2.4.7: the payload suffix chooses an assemble verb's canonical, not its
       reach. ``naming_vocabulary.classify`` reported ``_build_`` / ``_make_`` /
       ``_compose_`` / ``_construct_`` only when the name also ended in a payload
       suffix, which is a reach test written where a canonical test belonged, so
       the ratchet held at zero over 21 definitions wearing one. A reach test
       disguised as a canonical test is the shape to look for: it fails in the
       direction nobody checks, because the gate goes on reporting and its floor
       goes on holding. Also recorded: ``assemble`` / ``craft`` / ``forge`` have
       an addon-side population of 0, so the core gate's reading of them is free
       to promote whenever it is taken, and a bare assemble verb stays the core
       gate's alone.
   * - 6.16
     - 2026-09-06
     - §10.8: a read-only tier is the lowest rung of its privilege, implied by
       the lowest all-documents rung, with its own read rules and no dead rows;
       three hard-zero checks in ``readonly_tiers.py``. account's hidden
       building block becomes that rung.
   * - 6.15
     - 2026-09-05
     - ``[test_lint E8515]`` ``http-json-string``: a ``type="http"`` route
       returning ``json.dumps`` bare answers ``text/html``, which the client's
       ``post()``/``get()`` refuse; ``request.prepare_json_response`` is the
       spelling. The rule table also gains the ``E8514`` row it was missing.
   * - 6.14
     - 2026-08-31
     - §2.4 tightened against a rename pass over ``addons/stock``. New §2.4.22:
       reshaping the receiver is not producing a value -- a body that is one
       ``filtered`` / ``sorted`` / ``grouped`` / ``with_*`` call hands back the
       receiver reshaped, so it takes that operation's spelling and not a read
       verb, at 11 of 181 today. Also: ``selection=`` is a sixth
       field-declaration keyword ``field_hook_naming.py``'s ``ATTRS`` does not
       read, and a lambda that only forwards hides the binding from whatever
       does; ``_apply_`` is the Mutation row's largest unlisted spelling and the
       test is whether the object is a policy or a record; one operation split
       across two paired models is invisible to a search on either name and
       visible from the caller they share; and the cache table's three verbs are
       the drop side, with the fill side spelled four ways and canonically
       ``_prefetch_``.
   * - 6.13
     - 2026-08-31
     - §2.4 tightened against a rename pass over ``addons/point_of_sale``. New
       §2.4.21: a prefix is a claim, and the claim is checkable -- a protocol
       namespace claims the dispatcher reaches the name, ``action_`` claims the
       client hands the return to its action service (so an ``orm.call`` target
       is not an action, which is how §2.4.16's "a JS call" had been read), a
       ``_cb`` tail is that claim written backwards, and a predicate prefix
       claims a ``bool``. Also: where a name breaks three rules at once, rename
       once from the body's row rather than repairing them in turn; the caller's
       variable is the evidence an extension point's own body cannot give; and
       where the name and the body disagree completely the rename is a product
       question and the pass stops.
   * - 6.12
     - 2026-08-31
     - New §2.4.20, written against a rename pass over ``addons/project``: a zero
       on the abolished table means the sweep ran, not that the operation is gone
       -- ``_fill_`` / ``_purge_`` / ``_derive_`` are drained while
       ``_determine_`` / ``_populate_`` / ``_prune_`` / ``_seed_`` say the same
       four things, so the table is read as families and not as a word list.
       Also: ``_show_`` is a fourth predicate prefix and ``_helper`` is
       ``_impl``; a **public** ``check_*`` that returns instead of raising is the
       Validation row's blind spot, with §2.4.19 as its converse; ``_refresh_``
       is the fourth cache verb §2.4.17 declines to add; a reserved ORM verb on a
       dialog opener is ``action_open_*``; where a method name is also an XML id,
       match the syntax and not the name; and a formatter is run over the files a
       rename changed, never over the directory -- as neither is a whole-file
       write of a file five sessions share.
   * - 6.11
     - 2026-08-31
     - §2.4 tightened against a rename pass over ``addons/mrp``. §2.4.4: the
       variable a method returns is the strongest evidence for its name, and a
       first token repeating the model is what hides the verb. §2.4.6: a
       predicate named for the branch its caller takes is named for the wrong
       subject, and the receiver supplies the noun a verb owes. §2.4.7:
       ``_calculate_`` is the read family's ``_generate_``, and ``_prepare_``
       against ``_update_`` is settled on the parameter list, not the consumer.
       §2.4.9: where a tuple's products share a head, write the head once, and
       the descent wears the entry point's noun. §2.4.12: ``_post_`` before an
       ORM operation is the adverb *after*, not the verb; a ``_toggle_`` handed
       the new value is an ``_update_``; the Mutation row's discriminator is the
       write, not the ORM. §2.4.13: a function nested inside a method is the
       third ungoverned population and the largest, now gated at
       ``nested_helpers`` rather than left to a scanner.
   * - 6.10
     - 2026-08-31
     - §2.4 tightened against a rename pass over ``addons/hr``. §2.4.1: a hook
       prefix on a non-hook is a collision, because the spelling stays free for a
       real hook on another model. §2.4.5: ``2`` is the ORM's cardinality
       notation, not a spelling of ``to``. §2.4.8: an empty ``@api.constrains``
       is an extension point and neither of the two branches. §2.4.11: the
       reserved-prefix test applies to a ``@contextmanager`` unconditionally.
       §2.4.15: ``field`` / ``field_name`` governs a method name and an ``_ids``
       tail, not only a parameter. §2.4.16: the ``action_*`` discriminator reads
       from the XML as well as from the ``def``. New §2.4.19: a raising validator
       is a legitimate public RPC contract, and ``noupdate`` is the test for
       whether a server-action rename needs a migration.

   * - 6.25
     - 2026-09-02
     - §12.1 names one migration-directory spelling instead of accepting two.
       The bare module version is the convention and the series prefix is
       refused: the two agree inside a series and diverge across one, where the
       prefix re-runs a script the module has already applied. 62 directories
       were renamed and two ``test_lint`` gates hold it, one for the prefix and
       one for a name the loader cannot read at all.
   * - 6.24
     - 2026-09-02
     - §2.4's bare census counts leave the prose. A count whose only role is to
       be current now lives in one generated table in §2.4.3, rewritten in full
       by ``doc_restated_counts.py --update census``; a figure a sentence reasons
       from -- a ratio, a split, a zero -- stays in its sentence, and ``--update
       <name>`` refreshes one without banking the rest. Every sentence that lost
       its number was reread to stay true without it; §2.4.7's duplicated
       ``_prepare_`` backlog line and §2.4.13's stale "of the 574" went with
       them.
   * - 6.22
     - 2026-09-01
     - §2.5 gains the converse of *comments explain why*: a comment that carries a
       reason is **exempt from a pass that shortens prose**, and that exemption is
       what the category is for. The failure is not authors omitting such
       comments but a later commit condensing inline docs and taking one without
       reading it. The load-bearing-docstring rule beside it protects what a
       **machine** reads; nothing protected what only a **person** reads, which is
       the larger set -- there a strip emptied a block a gate parsed and the gate
       went vacuous, here a comment is read by nothing, so its removal moves no
       figure, breaks no test and leaves no evidence it existed. Evidence:
       `orm/validation.py`'s ``regex_pg_name`` lost both the reason for a
       deliberate divergence from upstream and the scope of the survey that made
       it safe. Also imports the actionable half -- deleting a comment is a
       separate decision from shortening one -- which had lived only in the
       workspace ``CLAUDE.md``, the split the change protocol exists to prevent.
   * - 6.21
     - 2026-08-31
     - §2.4.14's residual sweep gains its **inward** direction. The three clauses
       already there all start from an old spelling the sweeper knows about, so
       they make each author responsible for their own blast radius and leave the
       code that depends on a name undefended. The inversion -- enumerate what
       embedded or generated code depends on and confirm each dependency still
       resolves -- catches a rename by anybody rather than only one whose author
       swept, and it belongs to the dependent rather than to the sweeper, which
       makes it a test instead of a discipline.
   * - 6.20
     - 2026-08-31
     - Three prose figures re-derived, and two rules about what a rename's
       verification does not reach. The figures: ``exec_verbs`` 195 -> 192 and
       the ``_prepare_*`` count 766 -> 769, all three measured drifting at a
       pristine worktree of the commit that landed them and at its parent, so
       none was the working-tree artefact two sessions had separately read it
       as -- which is §1.4's own rule catching the sessions that wrote it. The
       rules, both §2.4.14: a **mock attribute** absorbs any name, so a stale
       assertion records zero calls and fails on the count rather than on the
       name, and neither a residual sweep nor a conservation count can see it,
       because a mock attribute has no definition anywhere; and the suite that
       covers an edited file is rarely the framework run a §2.4 sweep already
       has open, integration suites being in no ``testpaths`` and running only
       when named -- and its sharpest form, which has no tell, is a baseline
       that executed **no tests**: zero failures passes a failing-set comparison
       silently, so a run owes a test count before it means anything.
   * - 6.19
     - 2026-08-31
     - Six rules a §2.4 sweep of ``odoo/odoo/orm`` forced, every one of them
       ``[review]`` tier because both naming gates read 0 over that package
       before and after. §2.4.8 gains the **possibility** modal, whose repair is
       a reordering onto ``_can_`` rather than the rewrite necessity needs, and
       the **sibling family** as evidence cheaper than an annotation sweep.
       §2.4.4 gains the verification half of the generic-name rule: a scoped
       substitution fails silently and invisibly from the file being edited.
       §2.4.3 gains the converse of 6.16's reserved-row reading -- a reserved row
       can outrank the abolished row's printed canonical. §2.4.13 gains the two
       gates whose readings of 0 mislead differently, the sound one being the
       more dangerous. §2.4.14 gains the string-pin family: three ways a checker
       can hold a name without an import edge, the cleverest failing most
       obscurely. §2.4.14's root clause also gains its worked instance, a sweep
       rooted at a layout table that denied a repository existed.
   * - 6.18
     - 2026-08-31
     - §2.4.14 gains the residual sweep's three clauses, one per hole the other
       two leave, and the third is owed to a break rather than to an argument.
       The **root** is a glob over the workspace, never a list of repository
       names -- such a list is a cache of the filesystem, and a shared document
       cannot describe a machine-local checkout correctly for every machine at
       once; asserting one is absent is worse than silence, being a reason not to
       look. The **filter** is nothing: a 59 KB package README inside the package
       being swept is invisible to ``--include=*.py``. And a hit is **classified**
       against the embedded-interpreter sites, located first, because Python held
       in a string and run through an FFI ``eval`` is a call no naming gate,
       type-checker, test tier or Python-only grep can see -- the same class as
       the ``safe_eval`` of stored Python the migration rule already covers.
       Four other renamed names in that same tree were genuinely prose, the only
       difference being whether the name landed in a comment or inside the
       executed constant: a scan that cannot detect the failing case is not
       evidence about the passing one, and a rule that holds only when its author
       happens to type the shorter command is not a rule yet. No site count is
       recorded, deliberately -- it would re-derive to nothing elsewhere.
   * - 6.17
     - 2026-08-31
     - Eight rules a **second** §2.4 sweep of ``odoo/odoo/cli`` needed, the
       package having been swept once already (``9277fc322ff``, sixty-two names)
       and reading 0 on both vocabulary gates before and after -- so all thirteen
       are the ``[review]`` tier, and the section's own warning that a file can
       be sixteen names wrong and green is what a second pass measures. §2.4.5: a
       leading ``_to_`` is licensed by the **receiver**, so a module-level
       converter writes the pair (``_str_to_snake_case``). §2.4.6: ``_by_<key>``
       has two senses -- *a mapping keyed by* and *addressed by* -- and the
       second reads correctly, which is why it survives review; the test is the
       return, and ``cli/populate.py`` held both senses at once. §2.4.7:
       importing a Python file is a write, so ``get_upgrade_code_scripts``, which
       executed every script it returned, became ``load_upgrade_code_scripts``
       under §2.4.3's reserved verb. §2.4.9: an abolished execution verb in the **tail**
       hides from ``classify`` exactly as a noun in front does, and is false
       rather than vague where one collection feeds two opposite operations
       (``_get_fields_to_process``); and ``main`` is a binding to the process
       entry point, of which a program has one. §2.4.11: a context manager may be
       named for the noun it **yields**, which the no-verb rule never fires on
       because ``with`` reads as a declaration (``odoo_env`` ->
       ``open_environment``); and get-or-create hides under a bare ``_create_``,
       the tell being that the caller uses the return. §2.4.15: a parameter may
       not borrow a framework key it does not mean -- ``active_test`` naming
       something the body sets to ``False`` two lines above meant the opposite of
       what it said. §2.4.18: the ``_load_`` reservation, read literally,
       condemned every in-memory cache fill; it is against reading a *document*.
       Also §1.4: a gated figure is measured in the commit that **lands** it, the
       window being the review rather than the measurement.
   * - 6.16
     - 2026-08-31
     - Eight rules a §2.4 sweep of ``odoo/odoo/addons/base`` needed, the module
       reading 0 abolished verbs before and after -- the ``[review]`` tier only,
       and seventeen of the twenty-seven names were one family. §2.4.3: a
       reserved row is a claim about a **layer**, not about a word, so a
       filesystem probe is outside the ``exists`` row
       (``_addon_relative_path_exists``) exactly as ``pg_terminate_backend`` is
       outside ``_drop_``. §2.4.8: a third-person verb is a defect only where the
       **subject is not the receiver** (``matches``, ``owns_key`` stay;
       ``_escapes_own_record`` moves) and only where the verb is **dynamic** --
       the test is the progressive, *is rendering* against *is matching*; the
       larger half of the family has no part of speech at all (a participle, an
       adjective, a prepositional phrase) or wears the verb in the middle, where
       it is invisible to a ``_is_`` grep and to ``classify`` at once; a
       predicate prefix over a body that **writes** is an inverted claim rather
       than a weakened one, its tell is the last statement and its repair is
       usually the sibling three lines down (``has_field`` beside
       ``add_available_action``); and "a predicate may log" now carries a
       verdict, which is that the prefix wins. §2.4.10: the control-flow family
       splits **three** ways, the third being a body from which control never
       leaves at all (``_refuse_archived_user`` -> ``_is_user_archived``).
       §2.4.11: a borrowed ``_resolve_`` is as often taken from the receiver's
       own method one line below the ``def``, and the second wrong sense is the
       **constructor**, where ``_get_`` would be a second wrong answer
       (``_resolve_smtp_transport`` -> ``_prepare_smtp_transport``). §2.4.14: the
       residual sweep is rooted at the **workspace**, uncapped, and its survivors
       are classified per repository; prose divides into a mention and a citation
       an argument rests on; an accepted record is a fourth binding category, and
       "left as found" is not available for an ADR, because
       ``test_adr_coherence.py`` forbids it -- immutability is about the
       argument, not about a symbol's spelling, and the Amendments section is the
       reconciliation; a slot may mirror a **wire name** written outside the
       workspace, which reads as a misspelling (``_hasclass``). §2.4.17: name the
       fourth cache verb or the ban catches nobody (``refresh_``), and the
       memoised trio may straddle the public/private line. Also: the layer check
       proposes and §2.4.6's shadow test disposes; ``_assert_`` is another
       spelling of the Validation row; and the five prose figures five sweeps
       moved today are re-derived at ``813b5f68819``.
   * - 6.15
     - 2026-08-31
     - Eight rules a §2.4 sweep of ``odoo/http`` needed, the package having read
       0 on ``naming_core_vocabulary.py`` both before and after -- the
       ``[review]`` tier only. §2.4.4: a ``_by_`` after a **superlative** names
       the criterion a comparison ran on rather than a mapping key, so
       ``_get_classes_newest_by_identity`` returning a ``list`` is already right;
       and the head-noun type claim reaches a **singular** head naming a
       mechanism -- ``filter`` promises a callable, and three facts a filter
       would need are not one (``_get_endpoint_param_acceptance``). §2.4.5: a
       conditional tail is not the left operand, and ``to_Y_if_X`` leaves both
       searchable families at once (``_to_none_if_null`` → ``_null_to_none``).
       §2.4.7: where the hidden write and the return are **one decision**,
       neither the read verb nor the write's verb is honest and what is owed is a
       verb promising nothing about the absence of a write
       (``_get_serve_target_and_mode``, which installed the dispatcher its own
       caller never reads, → ``_select_serve_target_and_mode``). §2.4.8: the
       fourth offender of the http sweep, dropped from that paragraph as
       unattributable -- it is ``suppresses_uncommitted_warning`` →
       ``is_uncommitted_warning_suppressed``, a ``Protocol`` member declared in
       ``odoo/service``, which is why a package-scoped sweep could not reach it.
       §2.4.13: a closure named for the callee's **parameter** is worse than one
       named for its API, the parameter being the same word in every use of that
       API (``repl`` → ``replace_rule_arg_with_placeholder``). §2.4.14: when a
       core rename owes **no** migration -- ``safe_eval`` reaches a name only by
       attribute access from ``env`` / ``record`` / ``model``, so a module-level
       function is unreachable by construction and so is a method on a class
       those roots cannot reach; and a migration the manifest version has already
       passed is a change nothing will execute. §2.4.17: ``reset_`` promises a
       **source** and a per-owner initialiser has none -- a counter set to zero
       is a drop, not a rebuild (``_reset_thread_state`` →
       ``_clear_thread_state``).
   * - 6.14
     - 2026-08-31
     - Seven rules a second §2.4 sweep of ``odoo/db`` needed, after 6.13 drained
       the abolished verbs and left the ``[review]`` tier. §2.4.3: two verbs for
       one operation is a duplicate report only when neither verb is a **noun the
       file already owns** (``check_connectable`` beside ``probe_connectable``,
       which are a decision and an act); and a reserved verb frozen into a wire
       name is a reason to look, not to keep (``pools_evicted_stale`` →
       ``odoo_pool_evicted_stale_total``, a staleness drop wearing capacity
       eviction's verb -- left whole, and named so the next sweep does not
       rediscover it). §2.4.4: line the layers up, because the odd member of a
       family repeated at three layers is unobjectionable read alone
       (``ConnectionPool.drain`` → ``drain_all``), and a delegating body whose
       verb differs from its callee's is where it shows; the second owner of a
       name can be in the **same file**, which is the one shape where the rename
       itself is dangerous (``ConnectionPool.drain`` shadowed the
       ``psycopg_pool`` method four lines from its own call to it); and the
       member that already carries the right spelling is usually ten lines away
       (``drop_depending_views`` above ``get_views_depending_on_table``).
       §2.4.6: ``_each`` is one word of a family, and a tail naming *how* the
       members were chosen or *where* the work runs sits in the object's place
       too (``forget_keys_matching``, ``close_pools_in_background``); a temporal
       clause is a modality wearing another part of speech, and a wrapper that
       differs from its callee only by swallowing takes the callee's name plus
       ``_safely`` (``_reap_after_return`` → ``_reap_idle_pools_safely``).
       §2.4.8: an adjective-named ``@property`` promises a ``bool``, so returning
       a count is the ``has_unaccent`` lie one type over -- and the vocabulary
       the name declined to use was already written in the metric help text and
       the assertion message (``ConnectionBudget.exhausted`` →
       ``exhausted_count``). §2.4.17: a chain may not rename the operation at
       each frame -- a ``clear_`` may be one step of an ``invalidate_``, but the
       frame that decides *why* owes the correctness verb -- and ``_discard_`` is
       not a fourth cache verb, since it breaks the never-raise half of its own
       reservation.
   * - 6.13
     - 2026-08-31
     - Five rules a §2.4 sweep of ``odoo/db`` needed and did not find. §2.4.4: a
       word in front of the verb that is not a namespace is a modality and
       belongs in the tail as a condition (``_safe_close``, ``_maybe_reap_*``).
       §2.4.6: a *family* whose members differ only in the preposition has
       written the axis and left out every value on it, so the operands are
       written together or not at all; and a distributive tail is the plural of
       the operand, never ``_each``. §2.4.8: the predicate prefix is a claim
       about the return **type**, which a degrading three-valued ``Enum`` breaks
       silently (``has_unaccent`` → ``get_unaccent_status``); and a body that
       answers *and consumes* is an acquisition, not a predicate --
       ``acquire_*``, on the ``ConnectionBudget.acquire`` already in the tree,
       for the three interval throttles the package spelled three ways.
       §2.4.10: a builder of the *message* is the error family one step down and
       takes ``_get_*_message``. §2.4.13: the closure is a third population, and
       the place a bare execution verb survives longest. §2.4.14 gains the
       mechanics the section never had: a rename fails by under-reading (a capped
       binding grep) or by over-writing (a substitution that rewrites a local, a
       parameter or a dict key), both of them one failure -- a tool that cannot
       tell a definition from a use -- and neither fails a test; the untruncated
       residual sweep over every renamed name is what catches both, and a generic
       name is not renameable by substitution at all.
   * - 6.12
     - 2026-08-31
     - Four rules a §2.4 sweep of ``odoo/http`` needed and did not find. §2.4.4:
       a ``@property`` is named for the value, the one exception to *the verb
       leads* -- and no tool can tell one from a method, so every no-verb figure
       in the section is filtered or unstated. §2.4.8: a predicate spelled as a
       statement or an imperative is the same defect as one with no prefix, a
       different axis from ``_should_``'s modality. §2.4.10: ``_reject_`` /
       ``_abort_`` / ``_refuse_`` are the ``_raise_`` family under other
       spellings and split the same two ways, so abolishing one verb moved the
       defect. §2.4.13: a module-level ``a = b`` is a definition with no ``def``,
       invisible to the census and to the grep that would prove deleting it safe.
   * - 6.11
     - 2026-08-31
     - §2.4.1 gains the converse of the domain family -- a ``_get_domain_*``
       returns a ``Domain``, and is exempt from head-first reordering. §2.4.2:
       naming a constraint for its trigger *set* is the same defect as naming it
       for one trigger. §2.4.4: two more measurement cautions (a trailing
       qualifier alone flips ``collection_head_order``; the domain family scores
       ``tail`` wrongly), the head noun as a type claim about the members, the
       namespace-against-adjective-stack test, the ``_by_<key>`` mapping tail,
       and a qualifier constraining the input does not reorder. §2.4.14: an
       ``__all__`` entry is a position, not only a spelling -- ``ruff format``
       does not sort it and ``ruff check``'s RUF022 does. §2.4.8: the
       ``bool``-return pair is measured by ``_bool_annotated``, outside
       ``census()``'s model-class walk, so its population is wider than
       §2.4.3's and reaches neither nested functions nor plain classes;
       plus the hole where the union's two halves do not overlap, and a
       note that the section carries three scopes over two different trees.
   * - 6.10
     - 2026-08-31
     - Six rules a §2.4 sweep of ``odoo/cli`` needed and did not find. §2.4.7: a
       read verb may not hide a write -- both rows discriminate on where the
       return goes, so neither reaches a ``_get_`` that also converges stored
       state. §2.4.8: an unbound ``_check_`` that neither raises nor answers is
       advisory and is ``_warn_*``; and ``sys.exit`` / ``parser.error`` are the
       Validation row's ``raise`` in a program that has one. §2.4.9: an execution
       verb that IS the whole contract survives, with ``NoReturn`` as the proof
       -- which turns §2.4.10's weakest ground against ``_raise_*`` into the
       deciding one. §2.4.14: a slot filled by *reference* is free to rename and
       only a slot filled by *name* is frozen, and a slot's own spelling is a
       name too. §2.4.17: the three cache verbs bind names whose object is held
       state, so transient terminal output is outside the table and rows are not.
       §2.4.6 gains two limits on "a verb owes a noun" -- not where the noun would
       shadow the callee, and not where the method name is the word a user types --
       plus the warning that neither is "the receiver implies the object", which
       would take an agent-shaped class's whole convention with it.
   * - 6.9
     - 2026-08-30
     - §2.4.7: the core package is clean of the assemble verbs, and it is gated
       at zero rather than held by review -- ``classify`` reports ``build`` /
       ``make`` / ``compose`` / ``construct`` only on a payload suffix, which
       left 45 definitions in ``odoo/`` that a reading found and no count did,
       seven of them a bare verb. New gate ``naming_core_vocabulary``, over
       every function rather than over model classes.
   * - 6.8
     - 2026-08-29
     - §2.5: ``service/__init__.py`` and ``service/db/`` are no longer
       load-bearing docstrings. Their reader parsed ``odoo.service.__doc__``,
       the strip emptied it, and the gate then passed while detecting nothing;
       it was moved to ``doc/architecture/module.md``, which a strip cannot
       empty. The list promised a test that no longer exists.
   * - 6.7
     - 2026-08-27
     - Fact-check against the tree and a further narration cut. Corrections:
       every ``test_lint`` rule is an exact ratchet, so ``E8501`` does not "fail
       the build" and ``E8507`` is not advisory; the AST codes run to ``E8515``
       and six were undocumented; ``test_eslint`` does not exist; the manifest
       key order carries ``esm``; ``name_uniq_index`` is in ``mixin_catalog.py``;
       ``service/db.py`` is a package; the ratchet table is 13 of ~94 floors and
       the siblings carry ``naming_*`` scopes of their own; ``tests/loading`` is
       a third real-resource suite; §6.6's relaxation list had drifted from
       ``ruff.toml``; ``<group>`` in a search view takes no ``col``.
   * - 6.6
     - 2026-08-26
     - §10.8: a group reference must resolve -- an external id no group answers
       to reads as "not a member", so a typo hides a node from everyone and a
       negated typo shows it to everyone.
   * - 6.5
     - 2026-08-25
     - §10.8 gains ``write_groups``: a field everyone reads and only some may
       change had no spelling, and the computed boolean feeding
       ``readonly="not flag"`` that five places reached for enforces nothing.
   * - 6.4
     - 2026-08-25
     - A fourth Tier-2 path, ``tests/framework``: the facade ``__all__`` gate and
       the monkeypatch suite needed no database and now need no install.
   * - 6.3
     - 2026-08-23
     - Appendix A gains the order-line quantity swap: ``product_qty`` and
       ``product_uom_qty`` each carry the other's upstream meaning, writing the
       stored one silently half-lands, and the tree is ratcheted as
       ``orderlineqty`` rather than made to raise on day one.
   * - 6.2
     - 2026-08-22
     - §6.9 added: diff a run against its recorded failure set rather than
       re-running the suite; never count failures by grepping ``ERROR``; diff
       names, not counts.
   * - 6.1
     - 2026-08-22
     - Narration cut throughout, no rule changed.
   * - 6.0
     - 2026-08-22
     - Full rewrite into a direct, rule-first style; §2.4 gains numbered
       subsections §2.4.1--§2.4.17.
   * - 5.45
     - 2026-09-16
     - §10.5: a ``_search`` override that narrows visibility declares
       ``_search_visibility_fields``.
   * - 5.44
     - 2026-09-16
     - §6.4: ``assertQueriesConstant`` pins the shape of a batch's query count;
       the gates run as one command (``./gates.sh``) with a pre-push hook.
   * - 5.43
     - 2026-09-04
     - Every gate runs by hand: the CI workflows are gone, and the gate table
       and lint sections no longer name one.
   * - 5.42
     - 2026-08-22
     - §2.9.8: the constraint attribute names the columns; a rename is carried by
       module-data cleanup, not a migration, and it breaks the translations.
   * - 5.41
     - 2026-08-22
     - §2.4: a payload builder named for the operation it feeds borrows its
       caller's verb; the ``@api.constrains`` family is named for the condition
       it enforces; a ``Protocol`` declaration is a binding.
   * - 5.40
     - 2026-08-22
     - §2.4: running is a scheduler's domain operation; a callback is a role; a
       count of spellings is not a count of violations; provenance separates
       artifacts from arithmetic; the cache verbs are reserved for caches.
   * - 5.39
     - 2026-08-21
     - §2.4: a trailing preposition is an operand; the tail says which
       representation; ``field`` is a ``Field`` and ``field_name`` is a name.
   * - 5.38
     - 2026-08-21
     - §2.4: head-first is a test as well as an ordering; a memo takes the
       spelling of what it memoizes; a slot and its implementation are one
       contract; a shape suffix binds every override.
   * - 5.37
     - 2026-08-21
     - §2.2.1: mixins are named ``mixin.<what they add>`` -- prefix, not suffix.
   * - 5.36
     - 2026-08-20
     - §2.4: a domain builder leads with its object -- ``_get_domain_<what>``
       replaces the bare ``_domain`` suffix -- plus four bindings no checker
       reaches.
   * - 5.35
     - 2026-08-20
     - §2.4: an error is built here and raised there; a canonical verb can be
       wrong; an addition's tail names what is added.
   * - 5.34
     - 2026-08-20
     - §2.4: the execution-verb rule gains its first principled exception.
   * - 5.33
     - 2026-08-20
     - §2.4: wearing a dispatch prefix does not make a name a key.
   * - 5.32
     - 2026-08-20
     - §2.4: the assemble verbs are enforced for one shape; the payload suffix
       list is a search; object construction takes ``_prepare_``.
   * - 5.31
     - 2026-08-20
     - §2.4: what "name the domain operation" looks like, worked.
   * - 5.30
     - 2026-08-20
     - §2.4: ``exists`` joins the reserved verbs; the pure ORM reads move to
       ``_get_``.
   * - 5.29
     - 2026-08-20
     - §2.4: ``_find_`` is three operations wearing one verb; the
       class-membership blind spot covers module-level helpers and plain classes.
   * - 5.28
     - 2026-08-20
     - §2.4: the abolished table maps spellings, not methods.
   * - 5.27
     - 2026-08-20
     - §2.4: a module's own helpers are ungoverned; the object rule widens past
       collections; a provider noun is a namespace.
   * - 5.26
     - 2026-08-19
     - §2.4: the object leads its qualifier; the public form drops the
       underscore, not the verb.
   * - 5.25
     - 2026-08-19
     - §2.4: ``@api.ondelete`` gains a row; canonical
       ``_unlink_except_<case that raises>``.
   * - 5.24
     - 2026-08-19
     - §2.4: a decorator binding is out of the field-hook gate's reach by
       construction; a hook may hold two bindings.
   * - 5.23
     - 2026-08-19
     - §2.4: a hook's prefix is reserved for hooks; the verb leads;
       ``_generate_``; provenance as tiebreak.
   * - 5.22
     - 2026-08-18
     - §2.4's figures are derived rather than stated, through
       ``doc_restated_counts.py``; the census is re-scoped to this
       repository.
   * - 5.21
     - 2026-08-18
     - §1.4: a machine-doc figure is gated or frozen, never bare.
   * - 5.20
     - 2026-08-17
     - §7.2, §7.3: the task ID and the PR stop being mandatory.
   * - 5.19
     - 2026-08-15
     - §12.2: a removed Many2many keeps its relation table forever.
   * - 5.18
     - 2026-08-15
     - §12.2: a removed field's column goes in the same upgrade, and the harvest
       cannot be split across versions.
   * - 5.17
     - 2026-08-17
     - The ratchets: adds ``pyfunclen_addons``, the first ``--mode no-increase``
       floor.
   * - 5.16
     - 2026-08-14
     - Change protocol: cite the record, and write one where a rule is a
       decision.
   * - 5.15
     - 2026-08-15
     - §7.1 requires a pathspec to name files, not a directory.
   * - 5.14
     - 2026-08-15
     - §6.4 splits the query-count rule in three: get the stack, pin the
       guarantee, assert the mechanism.
   * - 5.13
     - 2026-08-11
     - §2.9.14 gains ``_defer()`` -- not finished is not failed.
   * - 5.12
     - 2026-08-10
     - §2.9.8 forbids UNIQUE over a translated column.
   * - 5.11
     - 2026-08-10
     - §8.3's re-export command corrected; deleting a string also needs a
       re-export.
   * - 5.10
     - 2026-08-09
     - pydocstyle retired: docstring presence is ``[review]``, only accuracy is
       mechanical.
   * - 5.9
     - 2026-08-09
     - The ratchets section states no count; the tool is the reading.
   * - 5.8
     - 2026-08-09
     - §12.2 named a module that does not exist; the helpers are in
       ``odoo/db/schema.py``.
   * - 5.7
     - 2026-08-09
     - Appendix A records ``date_planned`` → ``date_commitment`` on purchase.
   * - 5.6
     - 2026-08-09
     - §2.4 gains the cache lifecycle verbs.
   * - 5.5
     - 2026-08-08
     - §1.2 names the right requirements file, and when *not* to declare an
       external dependency.
   * - 5.4
     - 2026-08-07
     - Cyclomatic complexity is gated by a ``c901`` floor separate from ``ruff``.
   * - 5.3
     - 2026-08-07
     - ``test_lint`` gated; ratchets table completed.
   * - 5.2
     - 2026-08-06
     - §2.4 gains the verb vocabulary: canonical verb per operation, the
       abolished table, the reserved verbs, the *provisional* rules.
   * - 5.1
     - 2026-07-30
     - Corrections: ``force_company`` does not raise; ``<group>`` does carry
       attributes in search views; ratchets fail both ways; the
       ``at_install``/``post_install`` XOR is warned, not enforced; §2.9.4 and
       §12.1 corrected.
   * - 5.0
     - 2026-07-30
     - Full fact-check and rewrite. Countable gates become *ratchets* over
       committed floors; ``[label]`` markers replace 🔧/👁; the ``test_lint``
       layer documented.
   * - 4.2
     - 2026-06-30
     - XML IDs reversed from suffix back to prefix; the XML fixers, the
       single-line ``domain``/``context`` rule, sorter-then-formatter order.
   * - 4.1
     - 2026-06-23
     - §2.4 expanded: mail and framework-hook rows, naming-determines-section,
       field wiring, the class-eval ``default=`` note.
   * - 4.0
     - 2026-06-22
     - Linter claims reconciled with ``ruff.toml``; markers, TL;DR and glossary
       introduced; rules added for ``Command``, ``models.Constraint``,
       ``@api.model_create_multi``, multi-company, float comparison and modern
       typing.
   * - 3.0
     - 2026-04-20
     - Prior canonical revision (suffix XML IDs, 16-section model layout, Sphinx
       docstrings, unified 13-tag commit catalog).
