.. _coding_guidelines:

===========================
AgroMarin Coding Guidelines
===========================

:Version: 7.0
:Date: 2026-09-22
:Base: `Odoo 19.0 Coding Guidelines <https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html>`_
       + `OCA CONTRIBUTING.rst <https://github.com/OCA/odoo-community.org/blob/master/website/Contribution/CONTRIBUTING.rst>`_

The coding standard for the AgroMarin fork of Odoo 19.0. Authoritative where it
speaks; where silent, follow upstream Odoo 19, then OCA. Fix a stale claim in the
same change as the code that made it stale.

.. contents::
   :local:
   :depth: 2

----

How rules are enforced
======================

Each rule carries a label naming what catches it.

====================  =========================================================
Label                 Meaning
====================  =========================================================
``[ruff CODE]``       ``ruff check`` reports it.
``[test_lint CODE]``  A ``test_lint`` rule fails on it: an ``E85xx`` AST
                      checker, an XML rule named by rule (``data-root``,
                      ``duplicate-field``, ...), or a test named by test.
``[fixer NAME]``      A behaviour-preserving fixer owns the formatting. Run it;
                      do not hand-edit.
``[review]``          No tool checks it. A reviewer does (§9).
====================  =========================================================

Any remaining ``[ratchet NAME]`` means a ``test_lint`` floor: key ``NAME`` in
``odoo/addons/test_lint/tests/floors.json``.

A rule that reads like a lint rule may still be ``[review]``: ``ruff.toml``
disables some codes with a rationale. Trust the label, not the phrasing.

The floors
----------

.. list-table::
   :header-rows: 1
   :widths: 18 44 20 18

   * - Gate
     - Command (from the ``odoo`` checkout)
     - Held at
     - Runs in
   * - ruff
     - ``ruff check odoo/ --no-cache``
     - hard zero
     - ``gates.sh``
   * - ruff (tests)
     - ``ruff check tests/`` and ``ruff format --check tests/``
     - hard zero
     - ``gates.sh``
   * - mypy
     - ``-p odoo.orm -p odoo.db -p odoo.libs -p odoo.http -p odoo.service
       -p odoo.modules``; ``-p odoo.tools -p odoo.cli -p odoo.tests``
     - hard zero, mypy alone installed (never the workspace venv)
     - ``gates.sh``
   * - perf counts
     - ``./gates.sh --perf-counts``
     - ``tests/perf/floors.json``
     - ``gates.sh --perf-counts``
   * - ESLint
     - ``npx eslint .``
     - hard zero
     - ``gates.sh --js``
   * - ``tsc``
     - ``npx tsc --project tsconfig.json --noEmit``
     - hard zero
     - ``gates.sh --js``
   * - prettier (SCSS)
     - ``npx prettier --list-different "**/*.scss"``
     - hard zero
     - ``gates.sh --js``
   * - ``test_lint``
     - ``odoo-bin -i test_lint --test-enable --test-tags /test_lint``
     - ``floors.json``, exact both directions
     - by hand (needs a DB)

**CI** (``.github/workflows/gates.yml``) runs ``./gates.sh --perf-counts`` on
every push and pull request to ``19.0-marin``. ``--js``, ``--rust`` and
``test_lint`` run by hand.

**Move a floor by editing its JSON in the same change that moves the count.** A
gate with no entry is held at zero.

* **Every Python file in every repository is ruff-clean** ``[review]``. Only
  ``odoo/`` and ``tests/`` are gated; elsewhere ``ruff`` is pre-commit and
  review.
* **A finding on a file you touched may predate you.** Fix it (it is yours
  now); compare against ``git diff`` to attribute it.
* **Keep every function within ``[lint.mccabe] max-complexity`` (20)**
  ``[review]``. ``ruff.toml`` ignores ``C901`` in the main run; check with
  ``ruff check <path> --select C901``. Never raise the threshold to clear a
  finding.
* **Layer directions are those of** ``doc/architecture/module.md``.
  ``tests/framework/test_layer_contracts.py`` (Tier 2) enforces part of them;
  import cycles and the rest are ``[review]``.

The ``test_lint`` module
------------------------

``odoo/addons/test_lint`` holds AST checkers and registry-level tests for
Odoo-specific rules. **Every rule is an exact-match floor**
(``LintCase.assert_ratchet``): the count may neither rise nor fall without the
floor moving in the same change.

**Take a floor at the narrow scope**: only ``test_lint`` installed.

.. code-block:: bash

   odoo-bin --addons-path=odoo/addons,addons -d <db> -i test_lint \
       --test-enable --test-tags /test_lint --stop-after-init --no-http

Exception: classes that read the installed registry (bundles, dark siblings, ESM
specifiers, ``test_docstring``, ``TestSchemeDuplication``) are graded on a
fuller install; at the narrow scope ``test_docstring`` under-counts and
``TestSchemeDuplication`` skips.

AST rules (registry ``_rules.RULES``; engine ``_py_scan``; gate name
``lint_<rule_with_underscores>``):

=================================  =========  ==========================================
Rule                               Code       Catches
=================================  =========  ==========================================
``sql-injection``                  ``E8501``  Dynamic SQL built by interpolation
                                              (§10.4)
``gettext-variable``               ``E8502``  ``_()`` with a non-literal first
                                              argument (§8.1)
``gettext-placeholders``           ``E8503``  Two or more unnamed placeholders
                                              in a translated string (§8.1)
``gettext-repr``                   ``E8504``  ``%r`` in a translated string
                                              (§8.1)
``missing-gettext``                ``E8505``  Raw literal passed to a
                                              user-facing exception (§2.7)
``raise-unlink-override``          ``E8506``  ``raise`` inside an ``unlink()``
                                              override (§2.6)
``n-plus-one-query``               ``E8507``  Query call inside a ``for`` loop
                                              (§11.1)
``orm-import``                     ``E8508``  Addon runtime code importing
                                              ``odoo.orm`` (§2.1)
``onchange-domain``                ``E8509``  Domain returned from
                                              ``@api.onchange`` (§2.9.9)
``config-chainmap-patch``          ``E8510``  ``patch.dict`` over the config
                                              ChainMap; use
                                              ``config.patch(**values)``
``gettext-developer-error``        ``E8511``  ``_()`` around a builtin
                                              exception's message
``unique-over-translated-column``  ``E8512``  ``UNIQUE`` over a
                                              ``translate=True`` column (§2.9.8)
``shadowed-definition``            ``E8513``  A class body defining the same
                                              member twice
``tax-company-singular``           ``E8514``  ``t.company_id`` on
                                              ``account.tax`` (it has
                                              ``company_ids``)
``http-json-string``               ``E8515``  ``return json.dumps(...)`` from a
                                              ``type="http"`` route; return
                                              ``request.prepare_json_response(payload)``
``row-counter-in-test``            ``E8516``  ``sql_log_count`` in a test; read
                                              ``cr.sql_statement_count``
``null-exempt-composite-unique``   ``E8517``  Composite ``UNIQUE`` over a
                                              nullable column without ``NULLS
                                              NOT DISTINCT`` or an explicit
                                              partial ``WHERE``
``raw-egress``                     ``E8518``  Outbound call not routed through
                                              ``env["ir.egress"]``
``secret-in-environ``              ``E8519``  A secret written to
                                              ``os.environ``; pass the child its
                                              own ``env=``
``credential-storage``             ``E8520``  A secret in a plain column or
                                              ``ir.config_parameter``; use
                                              ``credential.credential``
``field-redeclared``               ``E8521``  A field declared twice in one
                                              class body
``default-evaluated-at-import``    ``E8522``  ``default=`` given a call's result
                                              instead of the callable
``selection-duplicate-key``        ``E8523``  A selection key listed twice
``field-hook-prefix``              ``E8524``  A field hook not named
                                              ``_compute_*`` / ``_inverse_*`` /
                                              ``_search_*`` / ``_selection_*``
                                              (§2.4.1)
``field-positional-argument``      ``E8525``  Positional field argument (§2.3)
``field-attribute-order``          ``E8526``  Field keywords out of
                                              ``FIELD_ATTRIBUTE_ORDER`` (§2.3)
``dead-field-attribute``           ``E8527``  An attribute setup ignores (§2.3)
``receiver-fail-open``             ``E8528``  An open route that should declare
                                              ``auth="receiver"``
``stored-related``                 ``E8529``  ``store=True`` on a many2one-only
                                              related field (§2.3)
``company-field-outside-config``   ``E8530``  A company setting declared outside
                                              ``mixin.company.config``
``auth-method-outside-owner``      ``E8531``  An auth method added to
                                              ``ir.http`` outside its owner
``hand-rolled-range``              ``E8532``  A classifying ``<x>_min`` /
                                              ``<x>_max`` pair; use
                                              ``mixin.band``
``route-untyped``                  ``E8533``  A program-facing route without
                                              ``typed=True`` and annotations
``sql-bound-placeholder``          ``E8534``  A bound parameter where PostgreSQL
                                              parses syntax (``IN %s``,
                                              ``INTERVAL %s``)
``noqa-rationale``                 none       ``# noqa`` without a rationale
                                              (*Suppressing a rule*);
                                              unsuppressable
``unreadable-source``              none       A file the scan cannot parse;
                                              unsuppressable
=================================  =========  ==========================================

Registry and tree gates carry no code and are named by test. The full set is
``odoo/addons/test_lint/tests/test_*.py``; the ones this guide cites:

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
     - ``lint_manifest_shape`` and ``lint_manifest_value`` (§1.2)
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
     - View-attribute vocabulary, kanban template scope, group-by filter with
       a domain, orphan labels, ``act_window`` view order, a ``menuitem``
       whose parent no module defines
   * - ``test_esm_specifiers`` / ``test_esm_bundles``
     - Unresolvable ``@addon/…`` import; undeclared ES-module bundle (§4.1)
   * - ``test_scheme_duplication`` / ``test_dark_sibling_scope``
     - Rules restated per colour scheme; dark-sibling placement (§5.3, §5.5)
   * - ``test_asset_paths_exist`` / ``test_bundles_assemble``
     - An ``assets`` glob matching no file; a bundle that does not assemble
   * - ``test_pofile``
     - Duplicate entries in a ``.pot`` file (§8.3)
   * - ``test_i18n`` / ``test_jstranslate``
     - Untranslatable static strings in templates and JS (§8.2)
   * - ``test_dunderinit`` / ``test_markers``
     - Module without ``__init__.py``; conflict markers or NUL bytes
   * - ``test_pep649``
     - Annotations that fail to resolve under PEP 649


Suppressing a rule
------------------

**Every suppression states why** ``[test_lint noqa-rationale]``: at least four
non-space characters, one a letter, after the codes.

.. code-block:: python

   value = compute()  # noqa: RUF015 — ordering is guaranteed by the caller

Bare ``# noqa`` and ``# noqa: CODE`` alone are violations. For ``E85xx``, both
``# noqa: E8501`` and ``# pylint: disable=sql-injection`` are recognised.
``ruff.toml`` ``per-file-ignores`` and the allow-lists in ``test_index.py`` and
``test_override_signatures.py`` are config changes, reviewed on their own
merits.

Quick Reference
===============

**Python**

* Double quotes, line length 88; every file ``ruff format``-clean (§2.1).
* One model per file, named after ``_name`` (§1.3) ``[review]``.
* Reach the ORM through ``odoo.api`` / ``odoo.fields`` / ``odoo.models``, never
  ``odoo.orm``, from addon runtime code (§2.1) ``[test_lint E8508]``.
* Every model declares ``_name`` and ``_description`` (§2.6) ``[review]``.
* Override ``create`` as ``@api.model_create_multi def create(self, vals_list)``;
  always ``super()`` in ``create`` / ``write`` / ``unlink`` / ``copy_data`` /
  ``default_get`` (§2.6) ``[review]``.
* Deletion constraints use ``@api.ondelete``; ``raise`` inside an ``unlink``
  override is a violation (§2.6) ``[test_lint E8506]``.
* Name new buttons ``action_*``; never rename an inherited core method (§2.4).
* One verb per operation: ``_prepare_`` builds payloads, ``_get_`` reads,
  ``_check_`` raises, ``_is_``/``_has_``/``_can_`` return booleans, ``_update_``
  writes, ``_add_``/``_remove_`` for collections. ``_build_``, ``_make_``,
  ``_fetch_``, ``_validate_``, ``_verify_``, ``_ensure_``, ``_do_``,
  ``_perform_`` are abolished, and ``_run_`` outside a domain verb (§2.4.3,
  §2.4.9); so are the ``_impl`` / ``_helper`` / ``_cb`` tails and ``_without_``
  (§2.4.17, §2.4.21, §2.4.22) ``[review]``.
* A ``default=`` that must stay overridable is ``lambda self:
  self._default_<field>()``; ``compute=`` / ``inverse=`` / ``search=`` take the
  method name as a string (§2.4.1) ``[review]``.
* ``odoo.fields.Command`` for x2many writes, never raw tuples (§2.9.7)
  ``[review]``.
* Never compare money or floats with ``==`` / ``!=`` / ``<`` / ``>``: amounts
  use ``currency.is_zero`` / ``compare_amounts`` / ``round``, other floats
  ``float_compare`` / ``float_is_zero`` (§2.9.12). Only ``==`` / ``!=`` is
  linted ``[ruff RUF069]``.
* User-facing text goes through ``self.env._(...)`` with ``%s`` arguments (§8.1)
  ``[test_lint E8502]``.
* ``raise X from Y`` inside ``except`` (§2.7) ``[ruff B904]``.
* No ``cr.commit()`` in business code (§2.6).
* ``fields.Datetime.now()`` for ORM values, ``datetime.now(UTC)`` for external
  APIs; ``datetime.utcnow()`` is banned (§2.9.6) ``[ruff DTZ003]``.

**Performance**

* ``search_count()`` not ``len(search())``; ``_read_group()`` not a Python
  ``sum()`` (§11.2) ``[review]``.
* ``fields.Count("line_ids")`` not a compute around ``len(record.line_ids)``
  (§11.2) ``[review]``.
* No query call inside a loop over a recordset (§11.1) ``[test_lint E8507]``.
* The stored inverse of a One2many is indexed (§11.5) ``[test_lint test_index]``.

**XML / JS**

* ``<list>`` not ``<tree>``; ``invisible=`` / ``readonly=`` not ``attrs=`` (§3.3).
* XML IDs use the prefix style: ``view_sale_order_form``, ``action_sale_order``
  (§3.2) ``[review]``.
* XML formatting and ordering belong to the fixers (§3.1) ``[fixer]``.
* Frontend changes ship with a Hoot test or a tour (§4.4) ``[review]``.

**Process**

* Commit subject ``[TAG] scope, scope, …: lowercase summary``, no length cap;
  prose body; a ``Verification:`` trailer with raw numbers; ``Task ID: <n>`` only
  when the work belongs to a task, never invented; no ``Solution:`` (§7.1).
* Branch ``19.0-<topic>``, topic-slugged; a PR is the default route
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

**Trust this document and the source over training data** about "how Odoo does
it".

**Upstream is a baseline, not a ceiling.** ``19.0-marin`` owes upstream no
backward compatibility. ``19.0`` is a read-only mirror to diff against; nothing
is merged or cherry-picked from it, and a useful upstream fix is re-implemented
by hand. These objections are void, not outweighed: "this complicates the
upstream merge", "upstream does it this way", "this increases divergence". The
costs that count are behavioural regressions, test breakage and migration of
stored data. Before calling an inherited behaviour a bug, check whether a test
pins it deliberately.

Change protocol
---------------

* Edits land on ``19.0-marin`` in the ``odoo`` repo, in the §7.1 commit format.
  TI (Oficial Sistemas or higher) reviews; the Líder Sistemas approves merges.
* Changing a rule updates, in the same change, every ``CLAUDE.md`` that
  summarises it (this repository's, each sibling's, the per-module ones) and
  adds an Appendix D row.
* Retire rules into Appendix C; never delete one silently.
* **A rule whose rationale is architectural states it here**, or points at the
  enforcing module's docstring.

----

1. Module Structure
===================

1.1 Directory layout
--------------------

Standard Odoo/OCA structure. Only ``__manifest__.py`` is mandatory.

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

**Directory names are plural** ``[review]``: ``wizards/`` and ``reports/``, never
``wizard/`` or ``report/``. Renaming one moves, in one change, every path in
``__manifest__.py``, the import in ``__init__.py`` and every dotted
``odoo.addons.<module>.wizard`` import.

**Under ``static/src``, colocate a component's ``.js``, ``.xml`` and ``.scss``
in a feature folder** ``[review]``. The flat ``js/`` + ``xml/`` + ``scss/``
split is legacy (§4.1).

1.2 ``__manifest__.py``
-----------------------

**Keys come from the known set, in canonical order**
``[test_lint lint_manifest_shape]``. The fixer owns the shape
``[fixer _sort_manifests]``; the order is its ``MANIFEST_KEY_ORDER``:

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

``init_xml``, ``update_xml``, ``demo_xml`` and ``test`` are deprecated
``[test_lint lint_manifest_value]``.

**The shape gate fails wherever the fixer would rewrite.** The fixer:

* drops a key equal to its ``_DEFAULT_MANIFEST`` value (``installable: True``,
  ``application: False``, ``auto_install: False``, ``data: []``,
  ``sequence: 100``); keeps ``version``; keeps ``auto_install: []``, which means
  *always*;
* strips ``name``, ``category``, ``author``, ``license`` and the URL keys;
* makes ``summary`` one line; drops a whitespace-only ``description`` (it would
  block the README fallback) or ``website``;
* lowercases ``countries``; drops an ``icon`` equal to
  ``/<module>/static/description/icon.png``; turns a ``set`` under ``assets``
  into a sorted list;
* writes strings as they are, never ``\uXXXX``-escaped.

**What the fixer cannot decide is a value finding**
``[test_lint lint_manifest_value]``:

* an unknown key or a wrong type;
* a ``version`` the loader marks uninstallable;
* a ``license`` outside ``ir.module.module``'s selection;
* a ``category`` with an empty segment or a root no
  ``ir_module_category_data.xml`` declares;
* a URL key without a scheme;
* ``depends`` naming itself, a duplicate, or a module on no addons path;
* an ``auto_install`` trigger outside ``depends``;
* ``external_dependencies`` of a kind other than ``python``, ``bin``, ``apt``,
  or an ``apt`` hint for an undeclared ``python`` dependency;
* a ``countries`` code that is not two letters, or one country with no
  ``l10n`` in the module name;
* a ``data`` or ``demo`` entry matching no file or listed twice; a ``demo``
  entry outside ``demo/``; a ``data`` entry under ``demo/`` or named
  ``*_demo``;
* an ``icon`` matching no file; a hook ``__init__.py`` does not bind;
* an ``assets`` bundle not named ``<module>.<bundle>``, not a list, or carrying
  an unknown directive.

Both gates read only the ``odoo`` checkout. Run them on the siblings by hand,
from the workspace root::

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
* **``auto_install`` only for a genuine bridge** between two independent
  modules, as ``sale_crm`` bridges ``sale`` and ``crm``.
* **A mixin is not a module by default** (§2.2.2).
* **Demo data lives in ``demo/`` and is listed under ``demo``** ``[review]``. A
  ``data/*_demo.xml`` is a misfiled demo file: move the file and the manifest
  entry together, and follow any code that loads it by path (``convert_file``
  in an onboarding action). A file listed under both keys is a data file; drop
  the ``demo`` entry.
* **Demo data reaches a workflow state through the workflow** ``[review]``.
  Create the record in its initial state and drive it with ``<function>``
  calls to the user's actions (``approval_app``'s demo calls
  ``action_confirm``); never write ``state`` or its dates directly. Why: a
  forged state skips every side effect of the transition.
* **A demo file must load** ``[review]``. Why: the loader catches the failure,
  logs *installed without demo data* and carries on, so nothing turns red. Load
  it with ``--with-demo`` on a server with an empty environment before landing.
* **A demo or data file never stores a secret** ``[review]``. A
  ``post_init_hook`` that generates one checks
  ``_is_encryption_key_configured()`` first; a file needing
  ``ODOO_API_ENCRYPTION_KEY`` fails on every server lacking it.
* **``license`` matches how the module is distributed**: ``LGPL-3``,
  ``OPL-1``, ``AGPL-3`` or ``OEEL-1``. Do not copy a neighbour's unchecked.

**External dependencies go in the manifest and in the owning repo's
requirements file** ``[review]``: ``requirements-addons.txt`` here,
``requirements.txt`` in the siblings. ``odoo/requirements.txt`` carries only
what the framework and always-loaded addons import.

.. code-block:: python

   "external_dependencies": {"python": ["requests"], "bin": ["wkhtmltopdf"]},

* **Use the PyPI distribution name**, not the import name (``python-ldap``, not
  ``ldap``); ``check_python_external_dependency`` resolves it through
  ``importlib.metadata``.
* **Declare only what the module cannot start without.** A dependency behind
  ``find_spec``, a function-local import or ``except ImportError`` is optional;
  declaring it turns a degrading feature into a refused install.
  ``base_import`` declares ``chardet``, not ``xlrd`` / ``odfpy`` /
  ``openpyxl``.
* **An ``auto_install`` module pins its dependency as a server requirement.**
  Why: ``_mark_auto_install_modules`` (``odoo/modules/db.py``) never consults
  ``external_dependencies``; only the UI install path checks it. ``cbor2``
  (``auth_passkey``) and ``ofxparse`` (``account_bank_statement_import_ofx``)
  are the cases.

1.3 File naming
---------------

**One model per file** ``[review]``. A ``.py`` under ``models/`` or
``wizards/`` declares exactly one ``Model`` / ``AbstractModel`` /
``TransientModel`` class, named after ``_name`` with dots as underscores. This
holds for ``_inherit`` extensions: fields added to ``sale.order`` go in the
module's ``models/sale_order.py``. ``models/__init__.py`` imports in dependency
order.

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
     - ``sale_order_demo.xml``; under ``demo`` in the manifest, never in
       ``data/`` (§1.2)
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
     - includes ``res.config.settings`` (§1.1)
   * - Reports
     - ``reports/{model_name}.py`` + ``_views.xml``; QWeb templates
       ``reports/{model_name}_templates.xml``
     - SQL-view report models and ``ir.actions.report`` records (§1.1)

1.4 Machine docs (``machine_doc_v*/``)
--------------------------------------

A module may carry ``machine_doc_v<N>/``: the machine-readable map of its
routes, models, architecture, conventions and test tags, read before touching
the module. Its figures are taken as premises.

**Every figure is gated or frozen; a bare figure is a defect** ``[review]``.

* **Gated**: derived by the module's ``factcheck.sh`` and asserted with its
  ``assert_doc_cites``. The default for anything cheap to re-derive. Never
  write a population count as a literal (``assert_eq "$(measure)" "31"``).
* **Frozen**: pinned to a named base commit, for readings that cannot be
  re-derived (a profile, a benchmark, an ad-hoc scan). The document names the
  base. **Never "correct" a frozen figure to a current value.**

**Gate measurements, pin invariants.** ``assert_eq "$(grep -c 'export class
Foo' …)" "1"`` is correct: the literal is the claim. Test: would the number
change under ordinary growth? Pin the invariant, not its incidental shape.

* **Pin every restatement**; better, do not restate.
* **Omit an incidental figure rather than gate it.**
* **A harness derives its roots from ``BASH_SOURCE``**, never a literal path.
* **A backticked path asserts the file exists**; the harness resolves every one,
  including inside a backticked command. Name a deliberately absent file in
  plain prose.

**Measure a gated figure at the commit that lands it** ``[review]``. Run
``git log --oneline -1`` immediately before ``git commit``; if HEAD moved since
you measured, re-measure. Measure in a detached worktree, never in the shared
checkout (§12).

**Run a module's ``factcheck.sh`` whenever you change the module or its machine
doc** ``[review]``. ``gates.sh`` runs only ``doc/architecture/factcheck.sh``.
Fork-wide assertions SKIP with a count when the repo is checked out alone.

----

2. Python
=========

2.1 Style and imports
---------------------

* PEP 8, **line length 88**, **double quotes** everywhere (strings, field
  attributes, docstrings).
* Import order: stdlib, third-party, ``odoo``, ``odoo.addons``, alphabetical
  within each group ``[ruff I]``.

.. code-block:: python

   import logging

   from odoo import api, fields, models
   from odoo.exceptions import UserError, ValidationError
   from odoo.fields import Domain
   from odoo.tools import LazyTranslate

   from odoo.addons.sale.models.sale_order import SaleOrder

**Reach the ORM through the public façade** ``[test_lint E8508]``. Addon runtime
code imports from ``odoo.api``, ``odoo.fields``, ``odoo.models``, never
``odoo.orm``. Tests are exempt. Why: the fork restructures ``odoo.orm``
freely.

**Every Python file is ``ruff format``-clean** ``[review]``; ``tests/`` is
gated. ``.pre-commit-config.yaml`` in each repo runs ``ruff-check --fix`` then
``ruff-format``; install it.

* **Lint, format, lint again.** ``# noqa`` binds to a line; a reflow moves the
  finding off it, the finding goes live and the orphan directive reports
  ``RUF100``.
* **Reformat a file you did not otherwise change in its own commit**, with lint
  re-checked.

2.2 Model class organisation
----------------------------

.. code-block:: python

   class SaleOrder(models.Model):
       _name = "sale.order"
       _description = "Sales Order"
       _inherit = ["mixin.mail.thread", "mixin.mail.activity"]
       _order = "date_order desc, id desc"

**Order members as below** ``[review]``. Section banners are not required
(§2.5: a comment must carry a why).

==  ====================  =====================================================
#   Members               Contains
==  ====================  =====================================================
1   fields                field declarations
2   indexes               ``models.Index()``
3   constraints           ``models.Constraint()``
4   constraint methods    ``_check_*``
5   CRUD methods          ``create``, ``write``, ``unlink``, ``copy_data``,
                          ``default_get``
6   compute methods       ``_compute_*``
7   search methods        ``_search_*``
8   inverse methods       ``_inverse_*``
9   onchange methods      ``_onchange_*``
10  action methods        ``action_*``
11  mail methods          ``_message_*``, ``_notify_*``, ``_track_*``
12  domain methods        e.g. invoicing
13  helper methods        ``_prepare_*``, ``_get_*``
14  hooks                 ``_auto_init``, ``init``, pre/post hooks
==  ====================  =====================================================

Among compute and onchange methods, define a method before the ones consuming
its output.

2.2.1 Mixin naming
~~~~~~~~~~~~~~~~~~

**A mixin's ``_name`` begins with ``mixin.``** ``[review]``, as a prefix; the
rest keeps its order. A mixin is an ``AbstractModel`` meant to be inherited
into other models. Class and file names follow ``_name`` (§1.3, §2.2).

.. code-block:: python

   # models/mixin_mail_activity.py
   class MixinMailActivity(models.AbstractModel):
       _name = "mixin.mail.activity"
       _description = "Activity Mixin"

**Not a mixin**, and keeps its name: an abstract model nothing inherits, such as
a QWeb report model (``report.{module}.{report_name}``) or an abstract service
model.

**Renaming a mixin is a code change, not a data migration.** It has no table;
the module update rewrites its ``ir.model`` row and ``ir.model.data``. The
rename reaches ``_name``, ``_description``, every ``_inherit`` naming it, the
file name, every literal model string in XML, CSV or Python, and every
``ref()`` of its ``model_<name>`` XML id. Renaming an inherited *method* to fit
§2.4 stays forbidden (Appendix C).

2.2.2 Where a mixin lives
~~~~~~~~~~~~~~~~~~~~~~~~~

**A mixin that depends on ``base`` alone and ships no data lives in ``base``**
``[review]``, in ``odoo/addons/base/models`` beside ``mixin.tag``,
``mixin.catalog``, ``mixin.band``. Why: ``base`` is in every closure, so it
costs no dependency.

**A mixin earns its own module only for**:

* **an external dependency**: ``mixin_encryption`` imports ``cryptography``,
  which ``base`` may not;
* **data, configuration or security of its own**: ``mixin_report_sql`` owns a
  materialized-view lifecycle and cron; ``mixin_attribute`` has a
  ``pre_init_hook`` and tables.

A ``depends`` beyond ``base`` counts only when the mixin reads that module's
models (``_inherit = "mail.thread"`` needs ``mail``).

**A mixin may live with the module that owns its subject matter only when every
intended consumer's ``depends`` closure contains that module** ``[review]``.
Compute the closure over every model that asks the mixin's question, not only
today's users. A consumer at or below the home in the graph makes the edge a
cycle and rules the home out. Example: the ``mixin.recurrence.*`` mixins live
in ``base``, not ``resource``, because ``ir.cron`` (in ``base``) consumes
``mixin.recurrence.interval``.

**A widget may live apart from its vocabulary**: the recurrence-update dialog
stays in ``resource``, where its only callers are.

**Moving a mixin between modules moves no stored data**; the migration
re-points ``ir_model_data``, from every module name a skipped release may still
hold.

2.3 Field conventions
---------------------

**Group fields semantically, not by type** ``[review]``. Relational fields mix
freely inside a group; no ``# <Noun> block`` comment is required (§2.5). **A
line model opens with the ``related=``
fields from its parent, the parent link (``order_id``) first.**

**Field names follow the table** ``[review]``:

====================  ==================  ==========================
Kind                  Convention          Example
====================  ==================  ==========================
Many2one              ``_id`` suffix      ``partner_id``
One2many / Many2many  ``_ids`` suffix     ``line_ids``
Dates                 ``date_`` prefix    ``date_validity``
Amounts               ``amount_`` prefix  ``amount_total``
Counters (new)        ``count_`` prefix   ``count_picking``; the existing
                                          ``*_count`` family is exempt
Quantities            ``qty_`` prefix     ``qty_transferred``; core
                                          ``product_qty`` / ``qty_done`` stay
Booleans              ``is_`` prefix      ``is_sent``
State                 ``_state`` suffix   ``invoice_state``
====================  ==================  ==========================

**A default that must stay overridable forwards to a ``_default_<field>``
method** (§2.4.1):

.. code-block:: python

   user_id = fields.Many2one(comodel_name="res.users", default=lambda self: self._default_user_id())

**Every field argument is a keyword, in one order, one per line**
``[test_lint E8525, E8526]`` ``[fixer _sort_field_attributes]``. Why: a
positional string could be the label, the comodel or the selection. The order is
``FIELD_ATTRIBUTE_ORDER`` in
``odoo/addons/test_lint/tests/_checker_field_declaration.py``:

#. what the field is: ``comodel_name``, ``inverse_name``, ``relation``,
   ``selection``, ``related``
#. what it says: ``string``
#. its shape: ``size``, ``digits``, ``currency_field``, ``translate``,
   ``sanitize``
#. how its value is produced: ``compute``, ``inverse``, ``search``,
   ``depends``, ``precompute``, ``default``
#. how it is stored and read: ``store``, ``index``, ``copy``, ``readonly``,
   ``required``, ``company_dependent``
#. what it points at: ``domain``, ``context``, ``ondelete``, ``check_company``
#. ``tracking``
#. any other attribute, alphabetically
#. ``groups``, then ``help`` last

With two or more keywords, put each on its own line and none on the call's line
(magic trailing comma). The fixer changes only argument spelling and order; a
comment inside the parentheses travels with its argument.

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

**Drop an attribute setup ignores** ``[test_lint E8527]``: ``index=`` on a
One2many, a Many2many or a non-stored compute; ``precompute=`` without
``store=True``; ``compute=`` beside a truthy ``related=``. Across ``_inherit``,
a ``related=`` overriding a parent's ``compute=`` takes a related field's
defaults (``compute_sudo=True``, ``readonly=True``), not the compute's.

**A boolean field attribute takes a Python bool.** ``store``, ``precompute``,
``copy``, ``recursive``, ``compute_sudo``, ``related_sudo``, ``required``,
``readonly`` and ``export_string_translation`` raise ``TypeError`` for anything
else.

**Never store a related field to make it groupable** ``[test_lint E8529]``. A
related field over many2one hops ending on a column already filters, groups,
sorts and aggregates in SQL through the join; ``store=True`` adds a copy every
source write rewrites on every child row. Keep the column, with
``# noqa: E8529  <what needs the column>``, only for a UNIQUE or EXCLUDE
constraint over it, or a composite index with a column of the model's own where
a measured plan shows the join losing. ``Binary`` and ``Image`` are exempt (a
stored ``image_128`` is a resize). Held at zero.

**Never store a related field for a constraint** ``[review]``. An
``@api.constrains`` naming a related field fires when the source changes,
stored or not (``recompute._fires_constraints``). The column is still needed for
a One2many's ``inverse_name`` and for the foreign key behind ``ondelete=``.

2.4 Method naming
-----------------

Every §2.4 rule is ``[review]`` except §2.4.1's field-hook prefix
``[test_lint E8524]``; beyond it, ``test_lint`` ``test_naming`` checks only that
no public method takes ``ids``/``context``.

**A method bound by the ORM wears its role's prefix** ``[review]``.

.. list-table::
   :header-rows: 1
   :widths: 20 20 36 24

   * - Prefix
     - Bound by
     - Contract
     - Example
   * - ``action_``
     - a button ``name=``; public
     - returns an action dict, or ``True``/``None``; new button methods only
     - ``action_confirm``
   * - ``action_view_``
     - a smart button
     - returns a window action over related records; a wizard opener may be
       ``action_open_*``
     - ``action_view_invoices``
   * - ``_compute_``
     - ``compute=``
     - no argument; assigns the field on every record of ``self``
     - ``_compute_amounts``
   * - ``_inverse_``
     - ``inverse=``
     - no argument; writes the field's value back to its sources
     - ``_inverse_quantity``
   * - ``_search_``
     - ``search=``
     - ``(operator, value)``; returns a ``Domain``
     - ``_search_display_name``
   * - ``_default_``
     - ``default=``
     - no argument; returns the default value
     - ``_default_warehouse_id``
   * - ``_domain_<field>``
     - ``domain=``
     - no argument; returns a ``Domain``
     - ``_domain_child_ids``
   * - ``_get_domain_<what>``
     - nothing (free-standing)
     - returns a ``Domain``
     - ``_get_domain_modules_to_load``
   * - ``_selection_<values>``
     - ``selection=``
     - no argument; returns the ``(key, label)`` list; named for the **values**,
       so one method may serve fields of several names
     - ``_selection_target_model``
   * - ``_onchange_``
     - ``@api.onchange``
     - no argument; mutates the form record; may return a warning dict
     - ``_onchange_partner_id``
   * - ``_check_``
     - ``@api.constrains``, or called
     - raises on failure; returns ``None``
     - ``_check_date``
   * - ``_unlink_except_<case>``
     - ``@api.ondelete``
     - raises when ``<case>`` holds; returns ``None``
     - ``_unlink_except_master_data``
   * - ``_prepare_*_vals``
     - nothing
     - returns the dict fed to ``create()``/``write()`` (§2.4.3)
     - ``_prepare_invoice_vals``
   * - ``_get_``
     - nothing
     - returns a value; no side effect (§2.4.3)
     - ``_get_candidate``
   * - ``_message_*`` / ``_notify_*`` / ``_track_*``
     - the mail protocol
     - as ``mail`` defines it
     - ``_track_subtype``

2.4.1 Field hooks
~~~~~~~~~~~~~~~~~

**Name a field hook for the field it serves, in full: ``_<prefix>_<field>``**
``[review]``. ``_default_category_id``, not ``_default_category``. A body shared
by several fields is named for what they have in common (``_compute_amounts``),
never for one of them. Several triggers maintaining one field: name it for that
field.

**A field declaration's hook keyword names a method carrying that keyword's
prefix** ``[test_lint E8524]`` for ``compute=``, ``inverse=``, ``search=`` and
``selection=``; ``[review]`` for ``default=`` → ``_default_*`` and ``domain=`` →
``_domain_*``. Why: a reader, and every checker, must tell a hook from a helper
by its name.

**Reserve the hook prefixes for hooks** ``[review]``. On a model class,
``_compute_``, ``_inverse_``, ``_search_``, ``_default_``, ``_onchange_``,
``_domain_`` and ``_selection_`` name only a method a field declaration or a
decorator binds. A body several hooks share is named for what it does
(``ir.cron``'s ``_compute_next_call`` → ``_get_next_call``). Why: an unbound
reserved name collides with a real hook of the same spelling on another model,
and a workspace-wide substitution cannot tell the two owners apart.

**A hook does one job** ``[review]``. If the declaring model also calls the hook
on ``self``, split it: the hook keeps the name and delegates to a helper.

**A method with a hook prefix takes no argument but ``self``** ``[review]``.
``compute=``, ``inverse=``, ``default=``, ``domain=`` and ``selection=`` call it
with nothing to pass, so a definition taking arguments is a helper: rename it.
``_search_`` takes ``(operator, value)``.

**Resolve every binding before calling a hook unbound** ``[review]``. A binding
is a quoted name (``default="_x"``), a bare name (``default=_x``), an attribute
(``default=self._x``), a forwarding lambda, or a constructed name
(``"_default_%s_template_fields" % model``). A constructed family renames
together or not at all; a tail that comes from stored data is not renameable
(§2.4.14).

**Triage an unbound zero-argument hook by the field, then by the body**
``[review]``.

* A field of that name exists on the model: the field may have lost its
  ``compute=``/``default=``. Read both; bind it or rename the helper. Never
  rename first -- a rename erases the only evidence of the lost binding.
* No model declares the field and nothing calls the method: delete it.

**A domain feeds ``search()`` and a field's ``domain=``, never
``create()``/``write()``** ``[review]``. Bound: ``_domain_<field>``.
Free-standing: ``_get_domain_<what>``, which returns a ``Domain``.
``_get_<what>_domain`` is abolished. ``_search_*`` is exempt: a domain is its
contract.

**The word ``domain`` in a method name means a search ``Domain``** ``[review]``.
A hostname, or a ``mail.alias.domain`` record, spells its own noun:
``_get_company_host``, ``_get_default_alias_domain``. A method named for what a
domain *reads* is named for that: ``ir.rule``'s ``_get_domain_keys`` →
``_get_context_keys_in_domains``. ``_get_domain_*`` is exempt from §2.4.4's
head-first reordering: the prefix is the family.

**A protocol namespace may open with a hook prefix when the continuation names no
field** ``[review]``: ``_search_panel_*`` promises no field ``panel_*``.

**Put the verb behind a protocol namespace and in front of a provider**
``[review]``. Protocol (what an overrider greps for): ``_search_panel_get_*``,
``_message_post``. Provider (where a value comes from): verb first, then
``_gc_`` / ``_weasy_``.

**Declare a field's SQL on the field; never override a model-wide SQL method for
one field** ``[review]``. The declarations and their method signatures:

.. list-table::
   :header-rows: 1
   :widths: 22 42 36

   * - Keyword
     - Method signature
     - Hook name
   * - ``value_sql=``
     - ``(field, alias, query) -> SQL``
     - ``_value_sql_<field>``
   * - ``group_by_sql=``
     - ``(field, alias, query) -> SQL``
     - ``_group_by_sql_<field>``
   * - ``order_by_sql=``
     - ``(field, alias, direction, nulls, query) -> SQL``, returned through
       ``_order_value_to_sql``
     - ``_order_by_sql_<field>``

Where the SQL is another field's, use ``group_by_field=`` / ``order_by_field=``
and write no method. Several fields sharing one body are named for what they
share. Do not override ``_field_to_sql``, ``_read_group_groupby`` or
``_order_field_to_sql`` for one field. Why: an override hides a per-field fact
behind a model-wide method, and ``rust_engine`` then serves the model's grouped
reads from Python. An aggregate of a non-stored compute needs no hook:
``_read_group`` folds it in Python. The overrides that remain are for what no
field declares: a custom granularity, an order term that is not a field, an
aggregate over a JSON column.

**A ``default=`` that must be overridable forwards through ``lambda self:
self._default_<field>()``** ``[review]``. Why: ``default=_default_x`` binds the
function object, so an override on an inheriting model is ignored.

**``compute=``, ``inverse=``, ``search=`` take the method name as a string, never
a lambda** ``[review]``.

.. code-block:: python

   user_id = fields.Many2one(comodel_name="res.users",
                             default=lambda self: self._default_user_id())  # Do
   user_id = fields.Many2one(comodel_name="res.users",
                             default=_default_user_id)                     # Don't
   total = fields.Float(compute="_compute_total")                          # Do

2.4.2 Decorator-bound families the gate cannot reach
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A decorator names its fields, not its method, so ``E8524`` does not reach these.
Every ORM-invoked hook is private.

**``@api.onchange``: ``_onchange_<field>`` for one field; ``_onchange_<what the
fields share>`` for several** ``[review]``. Never the public ``onchange_x`` /
``on_change_x``: it is reachable over RPC.

**``@api.depends``'s callable form returns field names:
``_get_fields_<field>_depends``** ``[review]``. A lambda in a declaration keyword
is itself the hook, so the method it calls takes the free-standing form.

**``@api.ondelete``: ``_unlink_except_<the case that raises>``** ``[review]``.
Take the case from the error: ``_unlink_except_master_data``, not
``_unlink_if_manual``. The verb is ``unlink`` because the hook guards the ORM
operation; never ``_remove_``, which names a business method that deletes
records. ``_unlink_`` without ``_except_`` performs a deletion.

**``@api.constrains``: ``_check_<the condition enforced>``** ``[review]``. Name it
for what must hold, never for its trigger or its trigger set:
``_check_at_least_one_administrator``; ``_check_root_delegated_fields`` →
``_check_delegated_fields_match_root``. A constraint binding one field is not
therefore ``_check_<field>``. Ask what raises.

**A hook holding two bindings wears one prefix** ``[review]``. A prefix does not
claim that no other binding exists.

**``selection=`` is a field-declaration keyword** and §2.4.1 governs it, module
functions passed by reference included (``_field_types`` →
``_selection_field_types``).

2.4.3 The verb vocabulary
~~~~~~~~~~~~~~~~~~~~~~~~~

**One verb per operation** ``[review]``. §2.4's table governs ORM-role prefixes;
every other method opens with a verb from the table below. An abolished spelling
is wrong, not dispreferred. §2.4.13 sets the scope; names fixed by an external
contract are exempt (§2.4.14).

.. list-table::
   :header-rows: 1
   :widths: 12 14 26 30 18

   * - Family
     - Canonical
     - Abolished
     - Return contract
     - Example
   * - Payload
     - ``_prepare_*``
     - ``_build_`` ``_make_`` ``_compose_`` ``_construct_``
     - returns values fed to ``create()`` / ``write()`` / ``Command``; no write
       (§2.4.7)
     - ``_prepare_invoice_vals``
   * - Read
     - ``_get_*``
     - ``_fetch_`` ``_retrieve_`` ``_obtain_`` ``_lookup_``
     - returns a value fed to anything else; no side effect (§2.4.7)
     - ``_get_candidate``
   * - Predicate
     - ``_is_`` ``_has_`` ``_can_``
     - --
     - returns a ``bool`` answering a question about the subject; never raises;
       no side effect
     - ``_is_addon_path_present``
   * - Validation
     - ``_check_*``
     - ``_validate_`` ``_verify_`` ``_ensure_`` ``_control_``
     - raises on failure, returns ``None``; a boolean answer is a predicate
     - ``_check_date``
   * - Mutation
     - ``_update_*``
     - ``_assign_`` ``_fill_`` ``_inject_``
     - writes to records; returns ``None``; an ``inverse=`` target is
       ``_inverse_<field>``
     - ``_update_qty_available``
   * - Addition
     - ``_add_*``
     - ``_append_`` ``_fill_`` (of a caller's container)
     - adds entries to an x2many, or to a dict/list **the caller passes in**;
       returns ``None``
     - ``_add_view_mode``
   * - Removal
     - ``_remove_*``
     - ``_delete_`` ``_purge_``
     - removes records or entries; ``unlink`` stays the ORM operation
     - ``_remove_view_mode``

**An accumulator is Addition** ``[review]``. A body that writes into a container
its caller owns and returns nothing is ``_add_``, not ``_fill_``. The
discriminator is who holds the container: a body that builds and returns a dict
is ``_prepare_``; one that writes onto records is ``_update_``.

**Reserved verbs carry one meaning each** ``[review]``. Use them only with it.

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - Verb
     - Reserved for
   * - ``_drop_``
     - SQL DDL -- ``_drop_table``, ``_drop_column``
   * - ``_insert_``
     - SQL DML, and insertion at a caller-given position -- ``_insert_cache``,
       ``insert_rows``, ``insert_paths(paths, bundle, index)``
   * - ``_push_``
     - stack or queue semantics -- ``push_protection``
   * - ``_discard_``
     - the ``set.discard`` contract: remove if present, never raise
   * - ``_append_``
     - a sequence whose **position is part of its contract**, adding at its end;
       abolished everywhere else
   * - ``read`` / ``write``
     - a method whose object is a **file**; the pair is one contract, never split
       across ``_get_`` and ``_write_``
   * - ``_resolve_``
     - a **partial** producer: returns the object, or ``None`` meaning *not
       applicable* (§2.4.11)
   * - ``_sync_``
     - convergence on a source of truth elsewhere (§2.4.12)
   * - ``fetch``
     - the ORM read into the cache: ``fetch()``, ``_fetch_field``,
       ``_fetch_query`` and ``backend.fetch`` are one contract and rename
       together (§2.4.11)
   * - ``flush_``
     - the ORM operation -- ``flush_model``, ``flush_recordset``
   * - ``_evict_``
     - **capacity** eviction: which entries go, not whether what stays is valid
   * - ``exists`` / ``_*_exists``
     - ``recordset.exists()`` and schema introspection -- ``_table_exists``,
       ``_column_exists``; never a predicate otherwise

**A reservation covers its layer, not its word** ``[review]``. Outside the named
layer the ordinary vocabulary applies: ``_drop_conn`` terminates backends and is
``_terminate_backends``; ``_addon_relative_path_exists`` asks the filesystem and
is ``_is_addon_path_present``. Inside the layer the reservation outranks an
abolished row's canonical: ``_inject(table, record_id, data)`` performs DML and
is ``_insert_row``, not ``_update_*``.

**``_drop_`` and ``_insert_`` are earned by the body** ``[review]``: it runs SQL
(``cr.execute``, ``SQL()``, a DDL/DML literal), returns a fragment annotated
``SQL`` for a caller that runs it, or (``_insert_`` only) places a member at a
caller-given position. Otherwise it is ``_add_``/``_remove_``.

**The reservation binds public names** ``[review]``. A button method opens with
``action_`` (§2.4); ``ir.actions.server.create_action`` / ``unlink_action``
(which neither create nor unlink an action record) and
``ir.cron.method_direct_trigger`` are renamed under §2.4.4's public-rename rule.

**``_apply_`` takes a named policy as its object** ``[review]``: a strategy, a
rule, a rounding, a discount (``_apply_putaway_strategy``,
``_apply_early_payment_discount``). A body that writes a record, field or quantity is
``_update_``.

**Read both halves of a paired model before choosing a verb** ``[review]``.
Template/variant, order/line, move/move line implement one operation under one
verb; the shared caller is where the split shows
(``_set_qty_available`` / ``_apply_qty_available`` → ``_update_qty_available``).

**Two verbs for one operation are a duplicate only when neither is a noun the
scope already owns** ``[review]``. ``check_connectable`` (decision) and
``probe_connectable`` (act) both stand where *probe* is a noun of the file.

**An exported wire name does not license the Python verb** ``[review]``. Rename
the Python half, keep the exported key, and name the half left in the commit
(``PoolStats.pools_evicted_stale`` → ``pools_discarded_stale``, a staleness drop
that wore capacity eviction's verb; ``odoo_pool_evicted_stale_total`` stays).

**Compare bodies, not only names** ``[review]``. Two definitions with identical
bodies are one definition. Siblings differing only in a namespace token
(``_l10n_ae_get_company_wps`` / ``_l10n_sa_get_company_wps``) move one layer
down; a module copied verbatim into sibling addons is extracted.

2.4.4 Ordering
~~~~~~~~~~~~~~

**The verb leads** ``[review]``. ``_import_retrieve_partner_vals`` hides its verb
behind ``import``. Two exceptions: a protocol namespace, and a ``@property``.

**A leading token is a verb, a qualifier, or a namespace by its grammar, never by
its frequency** ``[review]``. A token answering *what does this do* is a verb and
leads. A token that could follow *which* or *whose* is a qualifier or a
namespace. A noun-first prefix is a namespace only when it names a **protocol
several models implement** and would survive being moved to another model:
``_message_*``, ``_notify_*``, ``_track_*``, ``_portal_*``, ``_l10n_<cc>_*``.
An unlisted verb (``generate``, ``parse``, ``convert``, ``extract``) is resolved
under §2.4.20.

* **A first token repeating the model is not a namespace.** ``mrp.bom._bom_find``
  → ``_get_bom_by_product``.
* **A name with no verb gets one**: verb, object, qualifier --
  ``_root_model_names`` → ``_get_model_names_in_root_table``.
* **A namespace is a namespace in every name that wears it.** ``_gc_file_store``
  (gc the store) beside ``_gc_checklist`` (the gc checklist) →
  ``_get_gc_checklist``.
* **Layer namespaces in the order the calls nest.** ``_esm_run_esbuild`` wrapping
  ``_esbuild_invoke`` → ``_compile_with_esbuild`` / ``_compile_with_esbuild_locked``.
* **A modality in front of the verb goes to the tail as a condition.** Write the
  condition, not the hedge: ``_safe_close`` → ``_close_pool_safely``,
  ``_maybe_reap_idle_pools`` → ``_reap_idle_pools_if_due``. ``auto`` fused to a
  verb is the same defect (``_autoprint_generated_lot`` →
  ``_prepare_action_autoprint_generated_lot``); ``autovacuum`` and
  ``autocomplete`` are terms of art.

**A public method drops the underscore, not the verb** ``[review]``: ``get_*``,
``prepare_*``, down the table. **A public rename changes every repository in one
change or is not begun**: an RPC caller leaves no trace in any tree.

**A public method whose signature cannot cross JSON-RPC is private**
``[review]``: a return of recordsets, callables or exceptions, or a required
parameter of type recordset, ``fields.Field``, ``Callable``, ``Environment`` or
cursor. Making it private removes a surface; the public-rename rule does not
apply.

**A ``@property`` is named for its value** ``[review]``: ``session_store``,
``country_code``. A ``bool`` property may be an adjective (``closed``,
``enabled``). A no-verb scan excludes properties first.

**The object leads its qualifier** ``[review]``: ``_get_fields_readable``, not
``_get_readable_fields``; ``_get_port_effective``, not ``_effective_port``.
Scalars too. Reorder, then read the result:

* meaningless -- the qualifier was noise; drop it (``_get_related_assets`` →
  ``_get_assets``);
* unchanged in meaning, answering *whose* -- it is a namespace; leave it in
  front. A leading run naming a thing that exists (a template cache, an asset
  link, a record context) is a namespace: ``_get_template_cache_keys`` stays;
* reads and distinguishes -- reorder. Where the qualifier stood for a relation,
  write the relation: ``_get_related_bundle`` → ``_get_bundle_containing_path``.

A qualifier constraining the **input** does not reorder: ``get_single_database``
asserts about the list it receives.

**The head noun is a type claim about the return** ``[review]``. Ask what a member
**is**: ``_get_cached_template_prefetched_keys`` returned field names and is
``_get_field_names_in_cached_template``. A head naming a mechanism (``filter``,
``matcher``, ``resolver``, ``rule``) promises a callable or an object
implementing one; a tuple of facts about an endpoint is its signature
(``_get_endpoint_signature -> _EndpointSignature``).

**A ``_by_<key>`` tail directly after the head promises a mapping keyed on
``<key>``** ``[review]``: ``_get_template_views`` returning ``{ref: view}`` →
``_get_views_by_ref``. After a superlative, ``by`` is the criterion and the head
stands: ``_get_classes_newest_by_identity -> list[type]``.

**Take the name from the evidence the body already holds** ``[review]``, in this
order: the variable it returns (``bom_by_product`` → ``_get_bom_by_product``); a
sibling in the same file already spelling the noun phrase
(``get_views_depending_on_table`` → ``drop_views_depending_on_table``); the
vocabulary of its own log lines (logs ``circuit_open`` →
``_open_esbuild_circuit``).

**Line the layers up** ``[review]``. One operation at several layers carries one
name: ``ConnectionPool.drain`` beside ``EndpointRegistry.drain_all`` and
``odoo.db``'s ``drain_all`` → ``drain_all``. A wrapper whose verb differs from its
callee's on one line has found the defect. Where the aligned name would shadow a
module-level function in scope, §2.4.6's shadow test wins.

**Rename safely** ``[review]``.

* A name is not unique across the workspace. Prefer the already-qualified name;
  where a substitution is unavoidable, run the *other* owner's callers first.
* Where a class wraps a library object, check every bare verb against the wrapped
  API: ``ConnectionPool.drain`` shadowed ``psycopg_pool.ConnectionPool.drain``,
  which its own body calls.
* After a scoped rename, grep the **old** name across every repository and read
  each survivor.

2.4.5 Converters
~~~~~~~~~~~~~~~~

**Name a converter ``X_to_Y``; ``to`` is the verb** ``[review]``. The name is the
pair of representations, which keeps the ``_str_to_*`` and ``_*_to_sql`` families
searchable. ``verb_Y_from_X`` is fine: the verb leads and *from X* qualifies the
source. A name with no verb (``_db_id_from_xmlid``) is not; repair it by reading
the return, not by flipping the arrow.

**A converter returns the representation its name promises** ``[review]``. Four
limits:

* **A body that returns nothing is not a converter**, unless it fills an
  accumulator it is handed.
* **The conversion must be total in one operand.** An operand that steers the
  result leaves no pair to name: ``_paperformat_to_css(landscape, overrides)`` →
  ``_prepare_paperformat_css``.
* **Two representations of one value, not a value and its container.** A value
  guessed from a dict by a fallback chain is a read:
  ``_mimetype_from_values`` → ``_get_mimetype_from_values``.
* **A leading ``_to_`` needs a receiver that is the source representation**:
  ``attachment._to_http_stream()``. A module-level function or an unrelated class
  has no left operand: ``_to_snake_case(s)`` → ``_str_to_snake_case``.

**``convert_to_*`` is the field protocol and is reserved** ``[review]``.
``Field.convert_to_cache`` / ``_column`` / ``_record`` / ``_read`` / ``_write`` /
``_export`` name what the field converts **into**, and the ORM calls them. Nowhere
else may a name lead with ``convert``: ``X_to_Y`` already says a conversion
happens. ``_convert_amount_to_company_currency`` → ``_amount_to_company_currency``.

**``2`` is ORM cardinality notation only** ``[review]``. ``many2one``,
``one2many``, ``x2many``, ``_m2o``, ``_o2m``, ``_x2many`` are terms of art.
Everywhere else spell the converter: ``date2datetime`` → ``_date_to_datetime``.

**A condition is not the left operand** ``[review]``. ``_to_none_if_null`` hides
the name from both ``_null_to_*`` and ``*_to_none``; it is ``_null_to_none``.
Where the condition is the source representation, write it on the left. A real
condition on an otherwise total conversion is the second limit above: split the
name, do not qualify it.

2.4.6 Tails and operands
~~~~~~~~~~~~~~~~~~~~~~~~

**A verb that acts owes the noun it acts on** ``[review]``. An adjective or adverb
is not a noun and never takes the object's place: ``_warn_stranded`` →
``_warn_stranded_sources``, ``_reschedule_later`` → ``_reschedule_job_later``.
Three exceptions, and only these:

* **The receiver is the object.** On a recordset method ``self`` supplies it:
  ``_post_inventory``, ``_action_cancel``. The tail is still owed where the verb
  reaches one named part (``_update_cost_mode``).
* **The noun would shadow the callee.** ``Db.drop`` wraps ``drop_database``;
  ``self._drop_database`` would mean something else four lines away. Ask which
  spelling shadows (a builtin included: ``Db.list`` → ``list_databases``).
* **The name is a word a user types.** A CLI subcommand handler (``Db.init``,
  ``load``, ``dump``) is bound by shell history and runbooks (§2.4.14, third
  category). A private handler is not: ``Module._install`` →
  ``_install_modules``.

**An agent-shaped receiver does not imply the object** ``[review]``. Where a class
holds one thing and its siblings write the object (``import_python_module``,
``load_models``), a bare verb is the odd one out: ``announce`` →
``announce_module``.

**In an addition, the tail names what is added, not the medium** ``[review]``.
``_add_header_footer_html`` → ``_add_html_header_footer``. What is added is in the
parameters; what it is added to is the return.

**Never end a name with a preposition; write the operand** ``[review]``.
``_get_stream_from(record)`` → ``_get_stream_from_record``. Keep the preposition:
it carries the axis the family varies on. Where siblings differ only by
preposition (``get_maxconn_at`` / ``get_maxconn_for``), the preposition was
carrying a type: write every operand (``get_maxconn_at_endpoint`` /
``get_maxconn_for_readonly``).

**A distributive tail is the plural operand, never ``_each``** ``[review]``.
``_close_each(pools)`` → ``_close_pools``.

**A tail says which, how or where; the object is still owed** ``[review]``.
``forget_matching(predicate)`` → ``forget_keys_matching``;
``close_in_background(pools)`` → ``close_pools_in_background``.

**Never name a method for when it is called** ``[review]``. A temporal clause
stands in for the object and restates every call site. A wrapper that differs
from its callee only by swallowing takes the callee's name plus the modality
(§2.4.4, §2.4.10): ``_reap_after_return`` → ``_reap_idle_pools_safely``.

**Where neighbours return different representations, the tail says which**
``[review]``: ``_get_stream_placeholder`` (a ``Stream``) beside
``_get_placeholder_bytes``.

**Name a predicate for the question, in the tense the caller asks it**
``[review]``. Never name it for the branch the caller takes:
``_skip_bom_line(product) -> bool`` → ``_is_bom_line_skipped``.

**``_by_<key>`` means the return is a mapping keyed on ``<key>``, nothing else**
``[review]``. For *addressed by*, use ``_named`` / ``_matching``:
``_get_modules_by_name`` (returns a recordset) → ``_get_modules_named``;
``_prepare_model_factors`` (returns ``dict[model_name, factor]``) →
``_prepare_factors_by_model_name``. The test is the return, never the argument.

2.4.7 Payload against read
~~~~~~~~~~~~~~~~~~~~~~~~~~

**``_get_`` is not a default; decide ``_get_`` against ``_prepare_`` on the
consumer** ``[review]``.

* feeds ``create()`` / ``write()`` / ``Command`` → ``_prepare_*``, whatever its
  provenance;
* feeds a named non-ORM consumer (``safe_eval``, ``SQL``, a renderer, a
  constructor) → ``_prepare_*``, naming the consumer, not the shape:
  ``_prepare_eval_context``, not ``_prepare_eval_vals``;
* returns to a caller that only reads it → ``_get_*``.

Names fixed by a binding (§2.4.14), e.g. ``_get_report_values``, stay.

* **Tiebreak on provenance** ``[review]``. A built artifact (SVG, bytes, an
  object handed to a consumer) is ``_prepare_``; a scalar answering a question is
  ``_get_``, whatever arithmetic produced it.
* **A payload suffix (``_vals``, ``_values``, ``_data``, ``_dict``, ``_context``,
  ``_defaults``, ``_list``, ``_args``, ``_params``) is a search, not a verdict**
  ``[review]``. ``_get_action_dict`` returns ``read()`` output and is correct.
* **A noun is not a verb** ``[review]``. ``Report.barcode(...)`` →
  ``prepare_barcode``.
* **Never put a shape suffix on an extension point** ``[review]``; every override
  must keep it. ``_get_installed_addons_list`` → ``_get_addons_installed``.
* **Do not take the verb of the method one frame up** ``[review]``.
  ``_reflect_model_params`` feeds ``_reflect_models``: ``_prepare_model_vals``.
* **A canonical verb can be wrong** ``[review]``. ``_prepare_local_attachments``
  wrote and filtered with no consumer: ``_migrate_attachments_to_local``.
* **A domain is not a payload** ``[review]``. It goes to ``search()``: spell it
  ``_get_domain_<what>`` (§2.4). ``_prepare_badges_domain`` →
  ``_get_domain_badges``.

**``_generate_`` and ``_calculate_`` are not in ``ABOLISHED``; rename one by its
body when you touch it** ``[review]``. A built value or artifact is
``_prepare_``; a body that is one ``create()`` is ``_create_``
(``_generate_consume_moves`` → ``_create_consume_moves``); a write on existing
records is ``_update_`` (§2.4.12); a scalar answer is ``_get_``, whatever
arithmetic produced it (``_calculate_*`` → ``_get_*``). ``_build_``, ``_make_``,
``assemble``, ``craft`` and ``forge`` are abolished Payload verbs (§2.4.3,
§2.4.20).

* **A rename that collides is a duplicate report.** Give each derivation the tail
  that says which (``_get_duration_expected`` /
  ``_get_duration_expected_from_dates``); do not drop the second.
* **Rename the noun as well as the verb** when the field it names was renamed
  (``_calculate_date_finished`` → the getter of ``date_end``).

**Between ``_prepare_`` and ``_update_``, the parameter list decides**
``[review]``. A method that assembles the mapping is ``_prepare_``. A method handed
a mapping its caller owns, which adds to it, is ``_update_`` (§2.4.12), even when
it returns that mapping: ``_set_replenish_data(..., replenish_data)`` →
``_update_replenish_data``.

**A ``_prepare_*`` never writes** ``[review]``. A builder that calls
``create()``, ``write()`` or ``unlink()`` is named for that operation.

**A read verb never hides a write** ``[review]``. The test: can a caller who does
not want the write avoid it? A memo or a lazily filled attribute is exempt
(§2.4.10); a write to the database, the filesystem, another object's state, or
**importing a Python file** is not. Name the write and let the return ride
along: ``_get_module_model`` (which ran ``update_list()``) →
``_sync_module_list``. A reserved verb (§2.4.3 ``_load_``) is required where it
applies.

* **Where the write and the return are one decision, use a verb that promises no
  absence of writes** ``[review]``: ``_get_serve_target_and_mode`` (sets
  ``self.dispatcher``) → ``_select_serve_target_and_mode``. A choice that is made
  may be installed; a read may not.

2.4.8 Predicates and validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**A predicate is ``_is_`` / ``_has_`` / ``_can_`` and returns ``bool``**
``[review]``. Annotate it ``-> bool`` (§2.9.11). The three prefixes are reserved (§2.4.3).
A ``bool`` return does not make a predicate: ``write`` returns ``True`` by
convention, ``_coerce_bool(value, default)`` is a converter. Ask what the boolean
is -- an answer is a predicate, a converted value keeps its conversion verb, an
acknowledgement is neither.

**A predicate prefix is a claim about the return type** ``[review]``. A predicate
returning anything but ``bool`` is lying, most dangerously when the value
degrades to a correct truthiness (an ``Enum`` whose zero member is the negative).
Name the value: ``has_unaccent -> FunctionStatus`` → ``get_unaccent_status``.
Rename every carrier of the value together, attributes and wire keys included
(§2.4.14).

**A predicate prefix over a body that returns nothing is a mutator**
``[review]``. The tell is the last statement (an assignment, ``add`` /
``append`` / ``update``), not the annotation. ``has_field(...) -> None`` →
``add_available_field``. Look for the sibling that already spells it.

**Validation raises; predicates return** ``[review]``. ``_check_*`` is canonical
and matches ``@api.constrains``. ``_validate_``, ``_verify_``, ``_ensure_``,
``_control_`` are abolished for it (§2.4.3; scope §2.4.13); an ``_assert_`` in
production code is renamed by its body (§2.4.10). A predicate never raises: ``_can_execute_action_on_records``
(raised ``AccessError``) → ``_check_access_to_run``.

* **A ``_check_`` passes by returning and fails by leaving** ``[review]``.
  ``raise``, ``sys.exit`` and ``parser.error`` (``NoReturn``) all qualify. A
  ``_check_`` that returns normally on failure is a defect.
* **An ``@api.constrains`` hook raises ``ValidationError``** ``[review]``. One
  that never raises is either a constraint that owes the ``raise``, or advisory
  and owes a ``_warn_*`` helper called from ``create``/``write``. Exception: an
  empty hook that a downstream module overrides is an extension point
  (``hr.employee._check_ssnid``); an empty hook nobody overrides is dead -- delete
  it.
* **A ``_check_`` that neither raises nor answers is ``_warn_*``** ``[review]``:
  ``check_root_user`` → ``warn_running_as_root``. One that does something else is
  named for that: ``_check_faketime_mode`` → ``_create_faketime_now_function``.
* **An unbound ``_check_`` returning a payload is ``_prepare_``** ``[review]``:
  ``_check_contents(values) -> values`` → ``_prepare_contents``. Place a
  non-hook ``_check_*`` beside the operation it guards (§2.2).
* **A predicate may log** ``[review]``. The return is the contract; ``_warn_*``
  is for a body with no answer.

**Answer-and-consume is an acquisition: ``acquire_*``** ``[review]``. A method
that returns a ``bool`` **and** stamps state that changes the next answer (a
``_last_*`` write, a slot taken) is not a predicate: ``due_for_sample()`` →
``acquire_sample_interval``, on the model of ``ConnectionBudget.acquire``. Keep a
lock-free ``is_*`` pre-check beside it (``is_probably_due``). A predicate may
lock to read; it may not leave the object different.

**Modal prefixes are abolished** ``[review]``. ``should``, ``must``, ``need(s)``,
``want(s)``, ``requires``: ask the question and put the necessity in the tail --
``_should_stream_upload`` → ``_is_stream_upload_required``. A tri-state return is
not a predicate at all (``_wants_multi_company_group`` →
``_resolve_multi_company_group_membership``, §2.4.11). For possibility
(``may`` / ``might`` / ``could``) move ``_can_`` to the front and keep every
word: ``_groupby_spec_might_duplicate_rows`` →
``_can_groupby_spec_duplicate_rows``.

**Every predicate leads with its prefix** ``[review]``. These are the same defect
as no prefix:

* **a statement or imperative**: ``_hide_exception_internals()`` →
  ``_is_exception_detail_hidden``; ``_renders_pdf()`` →
  ``_is_pdf_rendering_enabled``;
* **a participle, adjective or phrase**: ``_all_branches_selected``,
  ``_jsonable``, ``_on_login_cooldown``;
* **a subject-first sentence**: ``_addon_is_present``;
* **a leading preposition**: ``_in_code_ranges`` → ``_is_within_code_ranges``.

A third-person **stative** verb whose subject is the receiver stays:
``FromFilter.matches(email)``, ``owns_key``. Test with the progressive: *is
rendering* is natural, *is matching* is not. Where the subject sits in the
parameter list, the receiver is an agent and the verb reads as an action
(``_escapes_own_record(vals)``): rewrite it. A ``@property`` is exempt (§2.4.4).

**A package is not a closed scope** ``[review]``. Read the declaration of every
``Protocol`` a package implements before calling it swept, and rename the
declaration, implementations, callers and fakes in one change (§2.4.14).

**In a family of predicates, the odd spelling is the finding** ``[review]``.
``caches_lang_dicts`` among ``can_scan_*`` → ``has_lang_dict_cache``.

**The abolished table maps spellings, not methods** ``[review]``. Its suggested
target is a hypothesis; the body wins. ``_verifies_tls`` is a predicate:
``_is_tls_verification_required``.

**An adjective ``@property`` returns ``bool``** ``[review]``. A count is
``<adjective>_count``: ``ConnectionBudget.exhausted -> int`` →
``exhausted_count``. Take the noun from the metric help, the assertion message or
the log line beside it.

2.4.9 Execution verbs
~~~~~~~~~~~~~~~~~~~~~

**Name the domain operation, not the act of running** ``[review]``. ``_do_`` and
``_perform_`` are abolished; ``_run_`` only under the domain-verb exception
below: ``_do_posting`` → ``_post_entries``. ``_execute_``, ``_process_``, walk
verbs (``_walk_``, ``_traverse_``) and ``_callback`` are provisional: prefer a
domain name where one exists (``_callback`` → ``_run_server_action``;
``_traverse_path`` → ``_get_update_path_target``); no mechanical rewrite.
``_handle_`` is idiomatic for an event or exception handler.

* **Where running is the model's domain, keep one verb and vary the object**
  ``[review]``: ``ir.cron``'s ``_run_jobs_until_deadline``, ``_run_job``,
  ``_run_job_within_budget``. The test: is there a more specific operation?
* **A protocol member moves as a batch** ``[review]``. ``ir.http._handle_error``
  is mirrored by ``HttpExtension`` in ``odoo/http/_protocols.py``: rename the
  Protocol, base, every override and the dispatcher in one change (§2.4.14).
* **A tuple return names both products or splits** ``[review]``. Same consumer →
  name both (``_prepare_body_and_stylesheets``); different consumers → split.
  Grep the workspace for consumers, not the file. Where both share a head, write
  it once: ``_get_intervals_available_and_occupied``.
* **A descent wears the entry point's noun; mechanics go in the tail**
  ``[review]``. ``_walk_forward`` → ``_get_slot_forward``.
* **A method whose whole contract is leaving is annotated ``NoReturn``**
  ``[review]``. Then an exit verb is honest: ``_exit_missing_subcommand``,
  ``raise_keyboard_interrupt`` (a ``SIGINT`` handler). An exit verb over
  ``-> None`` is a lie.
* **No execution verb in the tail either** ``[review]``. ``_to_process`` /
  ``_for_<verb>`` says only that the return is used: name the selecting property
  (``_get_fields_to_process`` → ``_get_fields_selected``) or the mapping
  (``_get_columns_by_table``).
* **A program has one ``main``** ``[review]``: the process entry point. Any other
  is verb and object: ``cli/server.py``'s ``main`` → ``run_server``.

2.4.10 Errors and stand-in names
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Build an error here, raise it there** ``[review]``. A method that builds an
exception is ``_prepare_*_error`` and **returns** it; write ``raise`` where
control leaves. Why: ``raise self._prepare_x_error()`` shows the exit;
``self._raise_x_error()`` hides it and is rarely typed ``NoReturn``.

.. code-block:: python

    # Don't
    self._raise_budget_error()
    # Do
    raise self._prepare_budget_exhausted_error()

* **A builder named as a noun phrase is this rule** ``[review]``:
  ``_budget_exhausted()`` → ``_prepare_budget_exhausted_error``;
  ``get_config_warning`` → ``prepare_config_warning``;
  ``_connection_test_error`` → ``_prepare_connection_test_error``. Read returns,
  not verbs. On a paired model, match the other half's spelling (§2.4.3).
* **A message builder is ``_get_*_message``** ``[review]``, used only where the
  message is shared and the exception class is not:
  ``_not_a_token(kind, value)`` → ``_get_invalid_name_message``. Prefer returning
  the exception.
* **Mind ``B904``** ``[ruff B904]``: a ``raise`` moved into an ``except`` owes
  ``from``.

**``_raise_``, ``_reject_``, ``_abort_``, ``_refuse_``, ``_deny_`` and
``_assert_`` are abolished** ``[review]``. They name control flow. Route by the
body:

* raises on a condition, returns nothing otherwise → ``_check_*`` (§2.4.8):
  ``_reject_oversized_body`` → ``_check_body_size``;
  ``_assert_filestore_dest_free`` → ``_check_filestore_dest_free``;
* raises unconditionally → ``_prepare_*_error``, raised by the caller:
  ``_abort_bad_request`` → ``_prepare_bad_request_error``;
* never leaves → it is a predicate: ``_refuse_archived_user`` →
  ``_is_user_archived``.

Absence from ``ABOLISHED`` does not permit a verb; the family is defined by what
the name talks about.

**A name standing in for another contract takes that contract's spelling**
``[review]``:

* a **wrapper** of a name the framework resolves at runtime takes the callee's
  spelling plus the verb: ``_empty_list_help`` → ``_get_empty_list_help``;
* a **memo** takes the spelling of what it memoizes: a memo over
  ``_resolve_path_def`` is ``_resolve_paths``;
* a **substitute** keeps the promise the default's name made;
* a **slot** (a callback parameter) and the method filling it share one name.
  Read the parameter list of every callback-taking constructor.

2.4.11 Partial producers and the ``_find_`` family
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**``_find_`` is not in ``ABOLISHED``: it covers several operations, so classify
each by its body** ``[review]``. A pure read is ``_get_``; search-then-create returning the record is ``_get_or_create_*``; a
derivation takes its own verb (``_find_available_name`` appends ``(2)``,
``(3)``: ``_get_available_name``); converging on a source of truth with no
return is ``_sync_*`` (§2.4.12: ``_find_existing_rule_or_create`` →
``_sync_rules``).

**Get-or-create hides under ``_create_`` too** ``[review]``. A ``_create_`` over
an existence check whose return the caller uses is ``_get_or_create_*``:
``_create_directory`` → ``_get_or_create_directory``. A ``_get_or_create_*``
returns the record; one that returns nothing is ``_sync_`` or ``_create_``.

**Read the caller of an extension point** ``[review]``. The base body is the
least informative in the tree: ``_migrate_remote_to_local`` returns
``self.type == "binary"`` but its caller discards the return; it is a
migration, not a predicate.

**``_resolve_`` is a partial producer: it returns the object or ``None`` meaning
*not applicable*** ``[review]``. A read that
always answers is ``_get_``.

* **The contract, not fetching, earns the verb.** ``_resolve_runner`` reads a
  dispatch table and returns ``None`` for an unmapped state.
* **``None`` must route somewhere.** Where ``None`` means *there is none*
  (``_get_stored_content``), keep ``_get_``.
* **Never borrow the verb from the body** (``Path.resolve()``,
  ``self.resolve(target)``): ``_resolve_targets`` (warns, returns ``[]``) →
  ``_get_target_paths``.
* **A constructor is ``_prepare_``** (§2.4.7): ``_resolve_smtp_transport`` →
  ``_prepare_smtp_transport``.

**Rename a private/public pair together or not at all** ``[review]``. A pair split
across two spellings is worse than a pair uniformly wrong.

**Name a context manager for the scope it opens, in the imperative**
``[review]``. The teardown is half the contract. ``_staged_filestore_temp`` →
``_stage_temp_file``; ``odoo_env`` (yields an ``Environment``) →
``open_environment``; on the model of ``savepoint``, ``borrow_request``,
``ignore_indexes``.

* **A context manager never wears a field-hook prefix** (§2.4.1): it cannot be a
  hook. ``_domain_errors_as_access_errors`` →
  ``_mask_domain_errors_as_access_errors``. Read the decorator before the name.

2.4.12 Mutation, sync and overloaded verbs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**A method that writes to records or to a caller-owned mapping is ``_update_``,
never ``_set_``** ``[review]``. The discriminator is the write, not the ORM: a
method adding to a ``dict`` its caller owns is this row (§2.4.7). Carve-outs, all
bindings:

* an ``inverse=`` target is ``_inverse_<field>`` (§2.4.1);
* ``set_values`` / ``get_values`` on ``res.config.settings`` are bound by name
  (§2.4.14);
* ``set_param`` on ``ir.config_parameter`` is public and called from JS and XML.

Where ``_set_x`` and ``_update_x`` coexist for one operation, merge them.

**A method that converges is ``_sync_*``** ``[review]``. Making one table agree
with a source of truth elsewhere creates the missing, writes the differing and
unlinks the gone. ``_synchronize_`` is ``[review]``, not abolished: rename it to
``_sync_`` where it is this operation. A name
announcing one branch of three is wrong: ``_reserve_paths`` (also moved and
deleted) → ``_sync_path_reservations``. Where a test and its method disagree
about the operation, take the test's word.

**``_post_`` has three meanings and gets no fourth** ``[review]``:
``account.move._post``, ``message_post`` and HTTP handlers. New code names the
domain operation. Distinct from these, ``post`` as the adverb *after* an ORM
operation stays, with the operation immediately behind it:
``_post_write_workcenter``, never ``_post_workcenter``.

**A ``_toggle_`` handed the new value is ``_update_``** ``[review]``. A toggle
reads the current value to pick the next. The new value arriving by any route --
a parameter (``toggle_is_reached(is_reached)``) or the name
(``_toggle_reconcile_to_true``) -- makes it an ``_update_``. ``toggle_lock`` and
``ir.cron.toggle`` (takes *which record*) are correct.

**A producer prefix over a body that returns nothing is this row** ``[review]``.
``_get_``, ``_resolve_``, ``_prepare_`` and ``_generate_`` each promise a return.
A body under one of them that returns or yields no value and instead stores into
something or writes records is ``_update_``, or the operation it really is:
``_prepare_request(url, kwargs)`` setting ``kwargs["timeout"]`` is an
``_update_``; ``_generate_missing_avatars`` (writes
``image_1920``) → ``_update_missing_avatars``; a body whose only write is
``create()`` → ``_create_*``. Not this row:

* a body that only raises (§2.4.8, §2.4.10);
* an extension stub (``pass``, docstring, bare ``return``, ``raise
  NotImplementedError``) whose overrides carry the contract;
* a method a field declaration binds as a hook (§2.4.1: ``_get_mo_count``
  assigning ``count_mo_*`` is a ``_compute_``);
* a public wizard button (§2.4.16).

A ``_get_or_create_*`` that drops the record it created is missing its
``return``: fix the body, not the name.

2.4.13 Scope, adoption and the ratchet
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**The vocabulary governs every function this workspace owns** ``[review]``:

* model methods (classes deriving from ``models.Model`` / ``TransientModel`` /
  ``AbstractModel``);
* every function in the core package ``odoo/``, at module level and on plain
  classes;
* every function in an addon, in **every** directory under its
  ``__manifest__.py`` -- ``models/``, ``wizard/``, ``controllers/``,
  ``tools/``, ``report/``, ``utils/``, ``hooks.py``, and ``migrations/``;
* functions nested inside another function, at any depth;
* module-level aliases (``a = b``) -- see below.

**Migrations are governed.** An upgrade script's helper is this repository's
code, reviewed like any other.

**Out of scope, as an explicit list:**

* ``fetch`` -- the ORM read operation, a row of the reserved table.
* ``append_paths`` -- the receiver is an ordered list and the item lands at its
  end (beside ``insert_paths``, which takes an index).
* Nouns spelled like verbs: ``fill_temporal`` (a ``read_group`` parameter and
  context key), ``on_delete`` (a field on ``ir.model.fields``), a *control*
  character.
* Vendored code under any ``_vendor/`` directory. It is not ours to rename.

**Read the return before the verb** ``[review]``. A ``bool`` return that never
raises is a predicate (§2.4.8), not a ``_check_``; a return of the value or
``None`` is ``_resolve_`` (§2.4.11); a function that returns a transformed value
is a converter, whatever its verb says. Example: ``validate_csrf`` → a predicate.

**A nested function takes the same vocabulary** ``[review]``. Grep ``\bdef `` (not ``^    def``) when sweeping a file.

**A closure passed as an argument is a slot** (§2.4.10). Name it for what it
does, never for the callee's parameter: ``repl`` →
``replace_rule_arg_with_placeholder``.

**No module-level alias of a function** ``[review]``. ``a = b`` binds a second
name for one operation. The only exception is the gettext idiom
``_ = get_text_alias``. Before deleting an alias, grep the alias's own name, not
its target.

**A gate reading 0 is not evidence** ``[review]``. Read the body of every name
you touch; a gated scope can still hold names that only ``[review]`` rules
catch.

**Adoption** ``[review]``. The vocabulary applies to all code, not only code you
create or rework. An abolished or misused verb found anywhere is a defect: fix
it in the change that finds it, or record it as debt.

2.4.14 Bindings a rename must carry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**A rename carries every binding of the old name, in the same commit**
``[review]``. ``git grep -ln '<name>' 19.0`` sizes the work against the
pristine mirror; it is an estimate, not a veto.

Checklist -- a rename must also update:

#. **XML** -- ``name="…"``, ``<button name="…" type="object">``,
   ``<menuitem action="…">``, ``xpath`` expressions onto those, ``inverse=`` /
   ``compute=`` / ``search=`` / ``default=`` wiring.
#. **JS** -- ``orm.call`` and every RPC by method name; ``mail``'s mock server,
   which reimplements Python members for HOOT.
#. **Sibling checkouts** -- overrides and callers in every repository of the
   workspace.
#. **``__all__``** -- re-sort it ``[ruff RUF022]``. ``ruff format`` does not
   reorder ``__all__``; only ``ruff check`` flags it, at a hard zero.
#. **Stored Python** -- code in database columns, run by ``safe_eval`` with
   ``env``, ``record`` and ``model`` in scope. Write a migration that rewrites
   the name in every such column: ``ir_act_server.code``,
   ``ir_actions_server_history.code``, ``ir_model_fields.compute``,
   ``hr_salary_rule.amount_python_compute``, ``hr_salary_rule.condition_python``
   (copy ``_STORED_PYTHON`` from the latest base migration, via
   ``odoo.tools.module_data.rename_in_stored_expressions``). Grep every
   repository's data files for the old name first; each
   ``<field name="code">``-shaped hit names a column. Only a method reachable
   by attribute access from ``env`` / ``record`` / ``model`` needs this; a
   module-level function, a closure, or a method on a non-model class is
   unreachable from stored Python.
#. **A new migration directory** -- never edit a shipped migration. Read the
   module's manifest version first; a database past that directory never runs
   it again.
#. **``default_<field>`` on ``res.config.settings``** -- a field rename owes a
   search for ``default_<old>`` on every settings model in every repository.
   ``set_values`` strips the prefix and ``ir.default`` raises on an unknown
   field.
#. **Context keys, registry strings and locals of the same spelling** -- decide
   each one; a text substitution takes them all (``report_action`` is both a
   method and a context key).
#. **Test pins** -- a ``patch.object`` / monkeypatch target reached by string;
   a checker that asserts a source string (``assertIn`` over ``read_text()``,
   a ``split()`` on a ``def`` line, a regex on a method's shape); the
   ``odoo.orm._protocols`` members pinned by the architecture tests. Grep the
   written call form (``._get_path(``), not only the symbol.
#. **Mock attributes** -- a ``MagicMock`` accepts any attribute, so a stale
   ``m.old_name.assert_called_once_with()`` passes silently or fails only on
   the count. Grep and run the test.
#. **Embedded interpreters** -- Python held in strings and run by ``eval`` /
   ``py.run`` / ``from_code`` in another language. Locate those sites first::

      grep -rn 'from_code\|py\.run\|py_run!\|include_str!' --include=*.rs

   A hit inside such a string or an ``include_str!`` target is a call.
#. **Machine docs** -- rewrite a citation of a live name; leave a *frozen*
   figure (§1.4) as it is. A name is not a figure.
#. **Prose** -- rewrite a citation an argument rests on; leave a changelog or a
   dated record (vault ``research/``, ``plans/``, ``workspaces/``); rewrite
   vault ``reference/``. Where a dated record's verdict has inverted (a
   PROVEN defect since fixed), say so in the record.
#. **Callers outside the workspace** -- a public method an integration calls
   over RPC, or a CLI subcommand. Treat it as a public-surface change; leave a
   delegating shim for the old name when removing it would break an external
   caller.

**A name assembled at runtime is a key, not a name** ``[review]``.
``getattr(self, f"_render_{report_type}")`` freezes the prefix, and the keys
are the enumerable domain of the variable half, not every name that starts with
the literal half (3 of the 15 ``_render_qweb_*`` are keys). Where the variable
half is a stored column (``ir.actions.server.state``), a rename needs a
migration.

**Dispatch through an explicit mapping, not ``getattr`` on a computed name**
``[review]``. Do: ``HANDLERS = {"code": self._run_code, …}``. Don't:
``getattr(self, f"_run_action_{self.state}")``. Why: a string key hides the
binding from every tool.

**A slot filled by reference is free; a slot filled by name is frozen**
``[review]``.

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Shape
     - What a rename costs
   * - ``parser.set_defaults(func=self._install)``, ``atexit.register(cb)``,
       ``signal.signal(SIGINT, handler)``, a ``Callable`` dataclass field
     - Nothing. Rename it and give it the noun §2.4.6 asks for.
   * - ``getattr(self, shell)``, ``getattr(self, f"_render_{report_type}")``
     - The name is a key. Do not rename it without migrating the keys.
   * - Python name mirroring a wire name used outside the workspace
       (``xpath_utils["hasclass"] = _hasclass``)
     - Neither moves; keep the two spelled alike and say so beside the
       registration.

The tell is whether the name appears as a string or as an expression. A slot's
own spelling is a name too: ``parse`` / ``modname`` fields called by
``parse_params`` / ``get_module_name`` state one contract twice.

**A new framework contract bound by name gets a declaration site** ``[review]``.
When the framework calls a method on a model it resolves at runtime
(``ir.actions.report`` → ``_get_report_values``), declare a new such method on
an ``AbstractModel`` the implementers inherit. Before renaming a conventional-
looking name, grep the framework for a bare call of it.

**A generic name is not renamed by substitution** ``[review]``. ``health``,
``snapshot``, ``due``, ``age`` belong to half the tree; rename those by reading
each site.

**The residual sweep is mandatory** ``[review]``. After the edit, grep every
old name:

#. over **every** renamed name;
#. with **untruncated** output -- no ``head``, ``tail``, pager or match limit,
   and no ``2>/dev/null`` or ``2>&1 | grep -v``; assert every root exists
   before searching;
#. rooted at the **whole workspace** by glob (``ls -d <workspace>/*/``), never
   at your own package and never at a list of repository names;
#. with **no file filter** (no ``--include=*.py``);
#. word-bounded (``grep -rn -w``).

Classify every survivor per repository: a local, a parameter, or a dict key of
the same spelling is legitimate; a call is not.

**Pair it with a conservation count** ``[review]``. Occurrences of the old name
at the base revision must equal occurrences of the new name at the tip
(``grep -o | wc -l``, at revisions, not in a dirty checkout). The sweep finds a
dropped call site; the count finds an over-written local. Procedure:
``agromarin-knowledge/reference/dev/verifying-a-rename.md``.

**Code that depends on a name owns a test that it resolves** ``[review]``.
Embedded or generated code (a string of Python run by another language) must
carry a test in its own suite that parses it and checks every private attribute
it reaches still exists.

**Verify with a run that covers the edited files** ``[review]``:

* Name the suite that covers the files in your diff and check that it runs
  them. A framework unit run does not cover an addon; nothing routine runs
  ``enterprise``'s suites.
* Read the test count before the failures. A run that executed zero tests is
  not green; a baseline owes a test count before it is compared.
* Check any extractor (``grep -oE`` over a log) against a number the run
  reports (``of N tests``, the ``Starting`` lines) before comparing runs with
  it.
* Count sites with the grep, never by eye.

2.4.15 Signatures
~~~~~~~~~~~~~~~~~

* **An override's signature must match its parent's**
  ``[test_lint test_override_signatures]``. Adding, removing or renaming a
  parameter, or changing its default, fails. This is what makes
  ``@typing.override`` (§2.9.11) meaningful.
* **Public methods may not take an ``ids`` or ``context`` parameter**
  ``[test_lint test_naming]``: both collide with the RPC calling convention.
* **A route handler's parameters are named by the route.** A parameter behind
  ``<string:field>`` is ``field``.

**``field`` is a ``Field``; a field's name is ``field_name``** ``[review]``.
A parameter named ``field`` annotated ``str`` is a defect, in core and in
bound-by-name hooks alike; the only exception is a route handler whose URL
segment is ``<string:field>`` (``_get_placeholder_filename(self, field: str)`` →
``field_name``). The same holds for a return: a ``_field`` tail returns a
``Field``, a ``_field_name`` tail a ``str``; an ``_ids`` tail returns ids, not a
recordset. Tell: a caller that immediately writes ``.ids`` on the result.

**A parameter may not borrow a framework key it does not mean** ``[review]``.
``active_test``, ``context``, ``ids``, ``domain``, ``company_id`` carry the
framework's meaning. Don't: ``_get_languages(..., active_test=True)`` meaning
"installed only". Do: ``installed_only=True``. Tell: the body sets the real key
to a constant beside the parameter.

**Grep the body for the other spelling before choosing one** ``[review]``. The
spelling in a user-facing message is usually the intended one:
``_get_version_periods(field=...)`` raising ``"… %(field_name)s …"`` →
``field_name``.

2.4.16 Placement
~~~~~~~~~~~~~~~~

**Naming fixes placement.** The prefix determines the §2.2 member group:

.. list-table::
   :header-rows: 1

   * - Name or decorator
     - Group
   * - ``create`` / ``write`` / ``unlink`` / ``copy_data`` / ``default_get``;
       ``@api.model_create_multi``; ``@api.ondelete``
     - CRUD methods
   * - ``_compute_*``; ``@api.depends``
     - compute methods
   * - ``_search_*``
     - search methods
   * - ``_inverse_*``
     - inverse methods
   * - ``_onchange_*``; ``@api.onchange``
     - onchange methods
   * - ``_check_*``; ``@api.constrains``
     - constraint methods
   * - ``action_*``
     - action methods
   * - ``_message_*`` / ``_notify_*`` / ``_track_*``
     - mail methods
   * - ``_domain_*`` / ``_selection_*`` (field hooks with no group of their own)
     - helper methods
   * - ``_prepare_*`` / ``_get_*`` and other internals
     - helper methods
   * - ``_auto_init`` / ``init``
     - hooks

The "domain methods" group is the module's business domain, not ``domain=``.

**A method the client invokes by name is ``action_*``, and only such a method**
``[review]``. Client invocation is an XML ``<button name="…" type="object">``,
a ``<menuitem action="…">``, or a JS ``orm.call``. It wears ``action_`` /
``action_view_*`` even when it returns nothing
(``generate_random_barcode`` → ``action_generate_random_barcode``). A method
that builds an action dict for Python callers is ``_prepare_*``. Search from the
XML and JS, not from the ``def``.

**Field wiring beats the name.** A method referenced by ``inverse="..."`` is an
inverse even if it is called ``set_*``; ``compute=`` and ``search=`` likewise
pin their targets. A method used as a field ``default=`` is evaluated at
class-creation time, so define it *above* the field block.
``_search_display_name(self, operator, value)`` is the Odoo 19 hook backing
``name_search``; ``_name_search`` does not exist -- do not define it.

2.4.17 Cache lifecycle verbs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**``invalidate_`` / ``clear_`` / ``reset_`` are the only cache-drop verbs, and
they are not interchangeable** ``[review]``.

.. list-table::
   :header-rows: 1

   * - Verb
     - Means
     - Failure it prevents
   * - ``invalidate_*``
     - Drop values that may be **stale with respect to the database**. The data
       is still wanted; it is no longer trustworthy.
     - Serving a value the database has since changed.
   * - ``clear_*``
     - Drop everything held, unconditionally: teardown, or handing the object
       to a new owner (stamping the new owner's start values included).
     - Leaking one transaction's, request's or database's state into the next.
   * - ``reset_*``
     - Rebuild derived state **from its source**. The state exists again
       afterwards.
     - Reasoning over a derived structure that no longer matches its source.
   * - ``_prefetch_*``
     - Fill a cache ahead of use (the fill side). Name what it warms:
       ``_prefetch_rollup_moves``.
     - Nothing observable; it costs queries, not correctness.

* **Do not add a fourth drop verb** ``[review]``. ``refresh_``, ``discard_``
  (reserved for the ``set.discard`` contract, §2.4.3) and ``purge_`` are
  abolished for cache drops. Read the body and pick a row:
  ``refresh()`` → ``reset_known_databases``; ``discard_cached_plans`` →
  ``invalidate_cached_plans``. A method that needs two rows does two things.
* **A counter set to zero is a drop, not a rebuild** ``[review]``.
  ``reset_`` requires a source; a per-owner initialiser has none and is
  ``clear_``: ``_reset_thread_state`` → ``_clear_thread_state``.
* **The fill verb is ``_prefetch_``, at the head** ``[review]``. ``_warm_``,
  ``_preload_`` and cache-sense ``_populate_`` are abolished; ``populate`` is
  reserved for the ``odoo populate`` CLI. Never put ``fetch`` in the tail
  (``_rollup_moves_fetch``): it hides the reserved ORM ``fetch`` (§2.4.3) from
  §2.4.4.
* **The verbs bind held state that a reader can be served stale** ``[review]``.
  The failure column is the scope. Transient output (erasing a terminal line)
  is outside it. **Rows are inside it**: a method that deletes rows is
  ``_remove_*`` (``_clear_schedule`` → ``_remove_triggers_due``).
* **The verb governs every name derived from the operation**, not only the
  method that performs it ``[review]``: ``_get_fields_invalidating_assets_cache``,
  never a local named ``clear`` feeding an invalidation.
* **Name a cache state with a participle of the state, not of the read**
  ``[review]``: ``loaded_bundles``, not ``fetched_bundles``. A method performing
  the read is still ``_get_*``.
* **A memoised read is three methods: ``_get_X`` / ``_get_X_cached`` /
  ``_get_X_uncached``** ``[review]`` -- the entry deciding the path, the
  ``@tools.ormcache`` wrapper, the body. When the entry is public, only the
  private two follow the pattern: ``list_dbs`` / ``_get_catalog_cached`` /
  ``_get_catalog_uncached`` (``odoo/service/db/listing.py``).
* **``_cache`` names the cache object; ``_cached`` names the memoised variant**
  ``[review]``: ``_get_view_cache`` vs ``_get_X_cached``.
* **``_impl`` and ``_helper`` are banned tails** ``[review]``. They stand where
  a discriminator was left unsaid; say it.
* **Choose the verb per frame, and let only the frame with a reason say
  ``invalidate_``** ``[review]``. A leaf that drops everything is ``clear_``
  whoever calls it (``clear_prepared_cache``); a frame that drops because of
  DDL staleness is ``invalidate_`` (``invalidate_catalog_facts``). A frame
  must not rename itself for the step below it.
* **A class whose drops differ in scope and reason shows both verbs**
  ``[review]``: ``TransactionSchemaCache.clear()`` calls
  ``invalidate_catalog_facts()`` and then drops ``locked_tables``.

2.4.18 The ingestion vocabulary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Reading an external document into records uses exactly these five verbs**
``[review]``. Stages after them use existing rows: mapping is ``_prepare_*``
(§2.4.7), writing is ``_update_*``, validating is ``_check_*`` / ``_is_*`` /
``_has_*``, reporting is ``_get_*``. Invent no verb for them.

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
     - representations → **candidate field values**, with provenance
     - ``_digitize_`` ``_mine_`` ``_pull_`` ``_ocr_``

**Acquisition: name what comes back, not the trip** ``[review]``.

* ``_download_*``: the result is a document this server takes from a remote
  service. Serving a file to a browser is a route or an ``action_``, never
  this row.
* ``_import_*``: the result becomes local records. A body that downloads and
  imports is ``_import_``; its cron is ``_cron_import_*``.
* ``_get_*``: the remote answer is not stored (a status, a lookup, a cached
  token).

**``_read_*`` knows formats and no business; ``_extract_*`` knows a document
type and no formats** ``[review]``. A method doing both is split.

**Use the canonical nouns** ``[review]``.

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

``attachment`` is the ORM record that may carry a document, not a synonym for
it. A function taking bytes takes a ``document``.

**The abolished verbs keep their meaning away from documents** ``[review]``.
``digitize``, ``interpret``, ``derive`` and ``sniff`` have no second sense and
are wrong everywhere. The rest are reserved:

* ``_parse_``: one scalar string in, one typed value out (``_parse_datetime``).
* ``_decode_``: an encoding with a key or scheme (``_decode_connect_token``).
* ``_load_``: the ORM operation, module loading, and filling held state from an
  authoritative source (``_load_field_catalog``). Never reading a document.
* ``_index_``: building a key → member mapping (``_index_by_grouping_key``).
  Producing text for a search index is ``_read_``: ``_index_pdf`` →
  ``_read_pdf_text``.
* ``_split_``, ``_scan_``, ``_detect_``, ``_ingest_``: their ordinary meanings,
  never applied to a document.

**Dispatch readers and extractors through a registry, never a mimetype-keyed
dict** ``[review]``. A reader declares the mimetypes it accepts and the
representation it yields, and registers itself; ``get_readers`` is the only
dispatch. Extractors also declare their cost, so the cheapest runs first.

2.4.19 What a Python-only reading misses
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Settle a public method's visibility at its callers, not its signature**
``[review]``. A public method whose whole contract is to raise is correct: the
client calls it to receive the error (``hr.version.check_contract_finished``,
called from ``button_new_contract.js``). Before privatising, run
``git grep -n '"<name>"' -- '*/static/src'``. §2.4.4's signature evidence holds
only one way: a non-serialisable *parameter* proves no RPC call exists; a
return value proves nothing.

**Check ``noupdate`` before renaming a method named in data** ``[review]``. A
server action or cron in an updatable ``<data>`` is rewritten on upgrade; one
inside ``<data noupdate="1">`` is not, so the rename owes a migration script
(§3.9). Read the flag on the enclosing ``<data>``, not the file.

**Sweep with ``\bdef ``, never ``^    def``** ``[review]``. Nested functions
(§2.4.13) are bound by the same vocabulary and appear in no
outline.

**JavaScript method names are a candidate list for the verb vocabulary, not
bound by it** ``[review]``. §4.2 governs JS naming. Rows whose discriminator is a
body (Removal: ``prune*`` / ``purgeStorage`` / ``_sweep``) may be applied by
reading the body. Framework contracts keep their spelling: OWL's ``validate``
prop key, ``Map``/``Set`` ``delete``, ``window.fetch``, and the ``make*`` factory
idiom (``makeEnv``). Ask what the body does, never what the token looks like.

**Grep the name in ``*.xml`` before renaming a component method** ``[review]``.
An OWL template calls methods by string (``t-on-click="foo"``); no linter
resolves it and the failure is at runtime.

2.4.20 Synonyms, and the verbs the table does not print
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Read §2.4.3 as families, not a word list** ``[review]``. For an unlisted verb,
ask which row's discriminator the body satisfies and take that row's canonical.
A zero count for an abolished verb does not mean the operation is gone.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Synonym
     - Canonical
   * - ``populate`` ``tweak``
     - ``_update_`` (Mutation)
   * - ``prune`` ``sweep``
     - ``_remove_`` (Removal)
   * - ``seed``
     - ``create``
   * - ``scan`` ``determine`` ``calculate``
     - ``_read_`` / ``_get_`` (Read)
   * - ``detect``
     - Predicate; Read where the body returns what it found
   * - ``synchronize`` ``synchronise``
     - reserved ``_sync_``, or ``_prepare_`` under a payload suffix
   * - ``assemble`` ``craft`` ``forge``
     - Payload verbs (§2.4.7), whatever the tail
   * - ``categorize`` ``categorise``
     - ``classify``
   * - ``note``
     - ``mark_`` (sets a flag) or ``record_`` (advances a counter), by body
   * - ``refresh``
     - a §2.4.17 verb by body; OAuth *refresh token* and
       ``REFRESH MATERIALIZED VIEW`` are nouns/SQL, not this verb
   * - ``sanitize`` ``sanitise``
     - by body, table below; HTML cleaning excepted

**Not synonyms, and kept** ``[review]``: ``reap`` and ``probe`` (terms of art,
reserved per §2.4.3); ``emit`` (``logging.Handler`` contract); ``locate_node``
(view-inheritance resolver); ``collect_`` (see below).

**``_sanitize_`` is abolished: it names a motive, not an operation**
``[review]``. Pick by body:

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

**``escape`` and HTML ``sanitize`` are reserved** ``[review]``. Same value in
another form: normalise. Same value made inert in a target syntax: escape, and
name the syntax (``_escape_export_cell``). Deliberately less than the input:
sanitise, only in the HTML cleaner layer (``libs/text/html``), and say what it
strips.

**``normalize_`` returns the input's type** ``[review]``. A body that turns
``dict | str`` into a ``frozenset`` builds a key: ``_normalize_dsn_key`` →
``_get_dsn_key``.

**``_save_`` is the reserved ``read`` / ``write`` case, not an ``ABOLISHED`` row**
``[review]``. Name the object's operation: a file is ``write``; a record is
``create`` or ``_update_``; an attachment row says which.

**A predicate prefix suspends the infix rule** ``[review]``. Behind ``is_`` /
``has_`` / ``can_`` / ``should_`` the tail's verb is the subject of a question,
not an operation: ``can_scan_identity`` is correct.

**``_show_`` is a predicate prefix outside ``ABOLISHED``; prefer ``_is_`` with the
modality in the tail** ``[review]``: ``_show_profitability`` →
``_is_profitability_shown``. A ``_show_X`` beside a
``_show_X_helper`` is two questions; name both subjects.

**A preposition-first predicate takes ``_is_`` / ``_has_``** ``[review]``:
``_in_code_ranges`` → ``_is_within_code_ranges``. A ``@property`` noun
(``cursor.in_pipeline``) is exempt.

**``collect_*`` is the Read row only when it returns the value it made**
``[review]``. Filling a container it did not create (a parameter, an attribute
of its receiver, a closure variable) is Addition on that container, not
``_get_``.

**A ``check_*`` that returns instead of raising is not a check** ``[review]``.
Public or private, rename by body: ``check_features_enabled`` (returns a dict)
→ ``get_features_enabled``; an optparse type checker (string → typed value) →
``parse``; a warning list → ``get_*_warnings``; a mimetype-or-falsy →
``_get_*_mimetype``; a ``bool`` about the subject → predicate. A check whose
only failure path is a helper's raise stays ``check_``. Read with §2.4.19: a
public ``check_*`` that only raises is correct.

**A producer prefix is a claim about the return** ``[review]``. ``_get_`` and
``_prepare_`` on a body that returns nothing are wrong: ``Field.prepare_setup``
→ ``reset_setup``; ``_prepare_missing_trees`` (fills ``state.trees``) →
``_add_missing_trees``. Excluded by definition: a producer that always raises
(a restricted override refusing its parent's contract), a Protocol member or
ABC stub, and an override that returns ``None`` because it has nothing to
give. A ``write`` call is not evidence of an ORM write (§2.4.3 reserves it for
files), and ``Command.create`` inside ``_prepare_`` is the canonical payload.

**A ``_get_`` that creates is ``_get_or_create_``** ``[review]`` (§2.4.11).

**``determine`` splits by body** ``[review]``: returns a value → ``get_``
(``determine_domain`` → ``get_search_domain``); performs an operation → that
operation's verb (``determine_inverse`` → ``apply_inverse``); assigns →
``set_``; dispatches → ``call_hook``. A family that looks undecidable often
contains two families.

**A reserved ORM verb never names a dialog opener** ``[review]``. A view
opener is ``action_view_*``; a wizard opener is ``action_open_*``
(``unlink_wizard`` → ``action_open_*``).

**Match syntax, not the bare name, when a method name is also an XML id**
``[review]``. Substitute the whole ``name="..."`` attribute in arch and the
call parenthesis in stored Python; keep the record id. Use word boundaries
(``\yunlink_wizard\y``) so longer names survive.

**Read every definition site before a whole-word substitution** ``[review]``.
The same name may be defined twice with different contracts
(``config._check_path`` vs ``ir.actions.actions._check_path``).

**Run ``ruff format`` only on changed files** ``[review]``:
``ruff format $(git diff --name-only -- '*.py')``. ``addons/`` and the sibling
repositories are not format-clean, and a directory-wide run rewrites files you
did not touch in a shared checkout.

**Never do a whole-file write in a shared checkout** ``[review]``. No
``git checkout -- <file>``, no copying a file back from a worktree. Read a
clean copy with ``git show HEAD:<path>`` outside the checkout, edit by anchored
hunk, and re-read the anchor before each write.

**Rules that a token scan misses** ``[review]``:

* **A bare verb obeys the body rules**: ``_resolve(settings)`` that always
  produces a value → ``_get_settings``.
* **A method returning a constructed exception** (never raising) is
  ``_prepare_*_error`` (§2.4.10); returning an exception or ``None`` for the
  caller to route is ``_resolve_*`` (``_translate_connect_error`` →
  ``_resolve_connect_error``).
* **A stand-in takes its callee's verb** (§2.4.10): a body that is one call to
  ``mark_locked`` is ``_mark_table_locked``; one call to ``exc.add_note`` is
  ``_add_*_note``.
* **``print_`` means ``print()``**. A logging body is ``log_*``
  (``print_log`` → ``log_sql_stats``).
* **One classification, one verb per package**: ``classify_query``, not
  ``categorize_query`` beside ``classify_statement``.
* **A verbless partial producer annotated ``Optional``** is ``_resolve_*``
  (``_replica_cursor`` → ``_resolve_replica_cursor``).
* **One thing, one noun per file**: ``get_foreign_keys`` returning names beside
  ``_get_fk_constraints`` returning rows → ``get_fk_constraint_names``.
* **One lossy typed conversion, one name**: ``_optional_int`` and
  ``_coerce_port`` → ``_coerce_optional_int`` (§2.4.5).

2.4.21 A prefix is a claim, and the claim is checkable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Every prefix is a checkable claim; check it** ``[review]``. A protocol prefix
(§2.4.1 field hooks, §2.4.16 ``action_``, a module's own namespace) claims the
protocol's dispatcher reaches this name: find the call. A return prefix claims
something about the return: read the body.

**Annotate a predicate's return ``-> bool``** ``[review]``: in the core package
``odoo/odoo/`` always (mypy gates it, §2.9.11); in addons, in new or changed
code. Why: the annotation turns the name's claim into something ``mypy``
checks.

**Group duplicate candidates by verb, object and return type** ``[review]``.
Name, body and type are three independent duplicate detectors (§2.4.3).

**A protocol namespace belongs only to names its dispatcher calls**
``[review]``. A model's private helper does not wear ``_load_pos_data_*``
unless the loader dispatches it (``_load_pos_data_country_ids`` →
``_get_referenced_country_ids``). A declaration site does not enforce this;
read the dispatcher.

**Every ``<button type="object">`` target is ``action_*``** ``[review]``
(§2.4.16).

**``action_`` means the client hands the return to its action service**
``[review]``. A JS ``orm.call`` that reads the return is ``get_*`` whatever the
invoker (``get_closing_control_data``). An ``action_*`` nothing invokes is not
an action, but check stored Python and ``noupdate`` data (§2.4.19) before
concluding nothing invokes it.

**The ``_cb`` tail is banned** ``[review]``. It names a role (§2.4.9) and not
the caller; a client-named button is ``action_*``
(``open_frontend_cb`` → ``action_open_frontend``).

**A predicate returns a ``bool`` about its subject and writes nothing**
``[review]``. When a name breaks several rules, find the row the body
satisfies and rename once: ``_is_journal_exist`` (searches, creates, returns
an id) → ``_get_or_create_journal_id``.

**A one-word public method name is read on sight** ``[review]``. It is a
domain operation on the receiver (§2.4.6) or unfinished: ``pos.make.payment.check``
→ ``action_make_payment``.

**Name an extension point by what its callers call the value** ``[review]``.
Read the call sites of an override point before its body:
``_unrelevant_records`` (returns ids; caller writes ``inactive_ids = …``) →
``_get_inactive_ids``.

**When name and body disagree completely, stop and ask** ``[review]``. The fix
is a product decision (an alias for one button, or deletion), not a rename.
``pos.config.close_ui`` (``return self.open_ui()``) is left as found pending
that decision.

2.4.22 Reshaping the receiver is not producing a value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**A method whose whole body is one ORM shaping call on ``self`` is named for
the shape** ``[review]``. It returns the receiver reshaped, not a produced
value; ``_get_``, ``_check_``, ``_set_``, ``_prepare_`` and ``_resolve_`` are
wrong on it.

.. list-table::
   :header-rows: 1
   :widths: 14 14 72

   * - Shape
     - Canonical
     - What the name carries
   * - Re-envelope
     - ``_with_*``
     - the same rows, a different environment (context, company, user,
       ``sudo``); the envelope is the subject
   * - Narrow
     - ``_filtered_*``
     - a subset of the receiver, never a row the caller did not hand in
   * - Order
     - ``_sorted_*``
     - the same rows in a stated order
   * - Group
     - ``_grouped_*``
     - a mapping whose values partition the receiver

.. code-block:: python

    # Don't
    def _set_view_context(self):
        return self.with_context(inventory_mode=True)

    # Do
    def _with_view_context(self):
        return self.with_context(inventory_mode=True)

* **Use the ORM's participle** ``[review]``: ``filtered``, ``sorted``,
  ``grouped`` are §2.4.10 stand-ins, not missing verbs. ``_filter_*`` is for a
  value subset (§2.4.20), never for wrapping ``self.filtered``.
* **``_without_*`` is banned** ``[review]``; name what comes back.
* **A shaping method without a prefix follows the table too** ``[review]``:
  ``phone.number._primary`` → ``_filtered_primary`` (a §2.4.14 batch with its
  template and catalogue callers).
* **Scope** ``[review]``: the rule covers a body that is one statement on
  ``self``. A method that searches and then filters returns rows the caller
  never held, and is a read.

2.5 Docstrings and comments
---------------------------

**Write no docstring and no comment unless one of these holds** ``[review]``:
the user asked for it; the file's local convention is docstrings; a test or a
reader parses the text; or the line records a non-obvious *why* -- a workaround,
a wrong-looking constant, an ordering constraint -- that the code cannot state.
Names and structure carry meaning; when they cannot, fix them instead of
annotating them.

**Never delete a load-bearing docstring** ``[review]``. These are read by code:

* ``odoo/cli/`` command docstrings -- the CLI help text (``cli/help.py``,
  ``cli/command.py``).
* Route handler docstrings -- the OpenAPI operation summary
  (``http/openapi.py``; ``http/tests/test_openapi.py``).

**A docstring that exists must be true** ``[ruff DOC102, DOC202, DOC403, DOC502]``
``[test_lint test_docstring]``. Its fields match the signature; update it in the
same edit that changes a signature, return type or behaviour. Use Sphinx fields
and ``"""triple double quotes"""``:

.. code-block:: python

   def _prepare_invoice_vals(self, order_line):
       """Return values accepted by ``account.move.create``.

       :param recordset order_line: lines to invoice
       :rtype: dict
       """

* A model is described by ``_description`` and each field's ``help=``, not a
  class docstring.
* Imperative, direct: "Return…", "Raise…". No *Basically*, *Note that*, no
  restating the name or the signature.
* A comment says why, never what.

**Deleting an existing comment is a separate decision from shortening one**
``[review]``. Leave it unless it is now false. Shorten around the reason, never
through it. Why: a comment is read by nothing, so its deletion fails no test --
``orm/validation.py``'s ``regex_pg_name`` lost the reason for its lowercase-only
form (PostgreSQL folds unquoted identifiers) this way.

2.6 ORM
-------

**Always call ``super()``** in ``create``, ``write``, ``unlink``, ``copy_data`` and
``default_get`` ``[review]``. Override ``copy_data``, not ``copy``.

**Override ``create`` in batch form** ``[review]``:

.. code-block:: python

   @api.model_create_multi
   def create(self, vals_list):
       for vals in vals_list:
           ...
       return super().create(vals_list)

**Every model declares ``_name`` and ``_description``** ``[review]``. Set
``_order`` when insertion order is wrong. Label records with ``_rec_name`` or an
override of ``_compute_display_name`` that assigns every record in ``self`` and
passes only the records it does not label to ``super()``. ``name_get`` does not
exist.

**Deletion constraints use ``@api.ondelete``** ``[test_lint E8506]``. Never
``raise`` inside an ``unlink()`` override. Why: the override also runs at
uninstall and blocks it.

.. code-block:: python

   @api.ondelete(at_uninstall=False)
   def _unlink_except_confirmed(self):
       if any(r.state != "draft" for r in self):
           raise UserError(self.env._("Cannot delete a confirmed order."))

**The framework owns transactions** ``[review]``. Never call
``self.env.cr.commit()`` or ``rollback()`` in business code. Only the framework,
the job and cron runners, and code holding its own cursor
(``self.env.registry.cursor()``) commit. Deferred or batched work is an
``ir.job`` (§2.9.14), not a commit loop.

**Assign fields directly in computes** (``self.field = value``); ``write()`` in a
compute recurses.

**Call ``check_singleton()``** first in any method that assumes one record.

**Propagate context with ``with_context``; scope companies with
``with_company``** ``[review]``. Never pass ``force_company``: it only warns, and
the call runs against the wrong company.

.. code-block:: python

   order.with_context(tracking_disable=True).action_confirm()
   order.with_company(company).action_confirm()

**Prefer recordset operations** -- ``filtered``, ``mapped``, ``sorted``,
``grouped`` -- over manual loops, and ``odoo.tools.groupby`` over
``itertools.groupby`` (it needs no pre-sorting).

**Design for extension.** No hard-coded values that belong in configuration.
Split methods so an override replaces one piece without copying the rest.

**Deprecate explicitly**:

.. code-block:: python

   @api.deprecated("Since 19.0, use _prepare_invoice_vals instead")
   def _prepare_invoice(self):
       return self._prepare_invoice_vals()

ORM performance -- counts, aggregation, batching, N+1, indexing, locking,
``ormcache``, cron batching -- is **§11**.

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

**User-facing exceptions take a translated message** ``[test_lint E8505]``. The
first argument of ``UserError``, ``ValidationError``, ``AccessError``,
``AccessDenied`` and ``MissingError`` goes through ``self.env._()`` (§8.1):

.. code-block:: python

   raise UserError(self.env._("Order %s cannot be confirmed.", order.name))
   raise RedirectWarning(
       self.env._("Please configure a default warehouse."),
       action_id,
       self.env._("Go to Settings"),
   )

**Never leak internals** ``[review]``. Log the traceback; show a generic message.

.. code-block:: python

   # Don't
   except Exception as e:
       raise UserError(str(e))

   # Do
   except Exception:
       _logger.error("Payment processing failed", exc_info=True)
       raise UserError(self.env._("Payment could not be processed.")) from None

**Fail closed** ``[review]``. Wrap each iteration in a savepoint; a failure rolls
back or moves the record to an explicit error state. Log-and-continue in
financial or state-mutating code is a violation.

.. code-block:: python

   for order in orders:
       try:
           with self.env.cr.savepoint():
               order._process_payment()
       except UserError:
           order.state = "error"
           _logger.error("Failed to process order %s", order.name, exc_info=True)

**Catch ``Exception`` only at an integration boundary** (external API, adapter,
job body) and only to log with ``exc_info=True`` and re-raise or set an error
state ``[review]``. Catch the narrowest type everywhere else. ``BLE001`` is
disabled in ``ruff.toml``, so review is the only check.

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
     - ``"http"`` (HTML/binary) or ``"jsonrpc"``; never the deprecated alias ``"json"``
   * - ``auth``
     - ``"user"`` (default), ``"public"``, ``"bearer"`` (API token), ``"none"``
   * - ``methods``
     - always explicit: ``["GET"]``, ``["POST"]``, …
   * - ``csrf``
     - default ``True`` for ``http``, ``False`` for ``jsonrpc``

**An overriding controller re-declares ``@route()`` without restating unchanged
attributes** ``[test_lint test_routes]``. Why: repeated ``type=``/``auth=`` hide
what the override changes. Controller security is §10.6.

2.9 Patterns
------------

2.9.1 ``Domain``
~~~~~~~~~~~~~~~~

**Build and combine domains in Python with ``odoo.fields.Domain``** ``[review]``.
Never concatenate lists or hand-write ``'&'``/``'|'`` prefixes. List-of-tuples
stays for static domains in XML and data files.

.. code-block:: python

   from odoo.fields import Domain

   combined = Domain("state", "=", "draft") & Domain("partner_id", "!=", False)
   either = Domain("type", "=", "out_invoice") | Domain("type", "=", "out_refund")
   negated = ~Domain("active", "=", False)
   Domain.AND([d1, d2, d3])
   Domain.OR([d1, d2])
   Domain.TRUE      # matches everything
   Domain.FALSE     # matches nothing

2.9.2 Recordset safety
~~~~~~~~~~~~~~~~~~~~~~

**``browse()`` of an id from outside the transaction is followed by
``exists()``** ``[review]``:

.. code-block:: python

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
     - suppress mail tracking on ``write()`` -- bulk imports only

A field may carry its own context for relational access:

.. code-block:: python

   child_ids = fields.One2many("res.partner", "parent_id", context={"active_test": False})

2.9.4 Monetary fields
~~~~~~~~~~~~~~~~~~~~~

**``fields.Monetary`` needs a companion currency field** ``[review]``. A missing
one fails an ``assert`` at registry build, and not at all under ``python -O``
(§10.3).

.. code-block:: python

   currency_id = fields.Many2one("res.currency", required=True)
   amount_total = fields.Monetary()                              # uses currency_id

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
     - f-strings -- extraction breaks ``[test_lint E8502]``
   * - Logging
     - ``%s`` args to the logger
     - f-strings ``[ruff G004]``
   * - SQL
     - ``odoo.libs.sql.builder.SQL`` with ``%s`` placeholders
     - f-strings -- injection ``[test_lint E8501]``
   * - HTML in errors
     - ``%``-style or ``.format()`` inside ``Markup()``
     - f-strings -- XSS

2.9.6 Datetime
~~~~~~~~~~~~~~

**Never call ``datetime.utcnow()`` or ``utcfromtimestamp()``**
``[ruff DTZ003, DTZ004]`` ``[ruff banned-api]``. Other ``DTZ`` rules are off: the
ORM stores naive UTC.

.. code-block:: python

   from datetime import UTC, datetime

   now_aware = datetime.now(UTC)          # external APIs
   now_orm = fields.Datetime.now()        # ORM Datetime values (naive UTC)

Comparing an aware value with a naive ORM value raises ``TypeError``. The server
pins the process timezone to UTC.

2.9.7 ``Command`` for x2many writes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Write x2many values with ``odoo.fields.Command``, never raw tuples** ``[review]``
(XML: ``[test_lint test_xml_lint]`` ``legacy-x2many-command``).

.. code-block:: python

   from odoo.fields import Command

   order.write({
       "line_ids": [
           Command.create({"product_id": p.id, "qty": 1}),   # not (0, 0, {...})
           Command.link(existing_line.id),                    # not (4, id)
           Command.set(new_line_ids),                         # not (6, 0, [...])
           Command.clear(),                                   # not (5, 0, 0)
       ],
   })

2.9.8 SQL constraints
~~~~~~~~~~~~~~~~~~~~~

**Declare constraints with ``models.Constraint`` / ``models.Index`` /
``models.UniqueIndex``, grouped as §2.2 orders them** ``[review]``.
``_sql_constraints`` is ignored by the registry (it only logs a warning).

.. code-block:: python

   _amount_check = models.Constraint(
       "CHECK(amount >= 0)",
       "The amount must be positive.",
   )
   _code_company_id_uniq = models.Constraint(
       "UNIQUE(code, company_id)",
       "Code must be unique per company.",
   )

**The attribute name is the constraint's database name
(``{table}_{attr}``): name the columns the definition names, in its order, then
the predicate suffix; a new unique constraint is ``<cols>_uniq``, a new CHECK
``<cols>_check``** ``[review]``. Do not sweep existing constraints to rename
them. Nothing verifies the name against the definition, and it appears in
``ir.model.constraint`` and every user-facing error.

**Rename a constraint without a migration** ``[review]``. Module-data cleanup
drops the old constraint on upgrade. **Do sweep the translations**: every
``i18n/*.po`` and the ``.pot`` reference it as
``model:ir.model.constraint,message:<module>.constraint_<conname>``; an unswept
reference silently reverts the message to English.

**Never declare UNIQUE over a translated column** ``[test_lint E8512]``. Why:
``translate=True`` is ``jsonb``, so the constraint compares whole translation
documents and stops firing once a second language is written. Use
``name_uniq_index()`` (``odoo/addons/base/models/mixin_catalog.py``), a
``models.UniqueIndex`` over the source term:

.. code-block:: python

   _name_src_uniq = name_uniq_index(
       "company_id",
       message="A template with this name already exists for this company.",
   )

It defaults to ``NULLS NOT DISTINCT``. When converting an existing
``UNIQUE(name, ...)``, pass ``nulls_distinct=True`` so only the comparison
changes -- existing data may rely on NULL scope columns not colliding
(``res.groups``).

2.9.9 Onchange
~~~~~~~~~~~~~~

**Derive values with ``compute=`` (``store=True, readonly=False`` when the user
may edit), not ``@api.onchange``** ``[review]``. Reserve ``@api.onchange`` for
UI-only behaviour and ``warning`` returns. Why: an onchange runs only in the form,
so imports, RPC and ``create()`` bypass it.

* ``@api.onchange`` takes plain field names; dotted paths are ignored.
* The method runs on a pseudo-record: assign fields or call ``update()``, never a
  CRUD method.
* **Never return a domain from an onchange** ``[test_lint E8509]``. Put dynamic
  domains on the field (``domain=``) or in the view.
* **An override must not narrow its parent's triggers**
  ``[test_lint test_onchange_triggers]``.
* A One2many or Many2many field cannot modify itself through an onchange.

2.9.10 Multi-company
~~~~~~~~~~~~~~~~~~~~

**Multi-company correctness is required everywhere** ``[review]``:

* Relational fields that must stay inside the record's company carry
  ``check_company=True`` (the model needs ``company_id``).
* Per-company scalar configuration uses ``company_dependent=True``.
* Read the active company as ``self.env.company``; scope with
  ``with_company(company)``. Never hard-code a ``company_id``.
* Company record rules use ``[("company_id", "in", company_ids + [False])]``
  (§10.8).

.. code-block:: python

   company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
   warehouse_id = fields.Many2one("stock.warehouse", check_company=True)
   default_journal_id = fields.Many2one("account.journal", company_dependent=True)

2.9.11 Type hints
~~~~~~~~~~~~~~~~~

**Annotate every parameter and return type in framework code (``odoo/odoo/``
outside ``addons/``)** ``[review]``; mypy gates it
(``gates.sh``). ``ANN`` is linted only in ``odoo/libs/`` and
``odoo/orm/components/`` ``[ruff ANN]``. **In addons, annotate predicates
``-> bool`` in new or changed code** (§2.4.8); elsewhere in addons, hints are
optional. PEP 649: forward references need no quotes.

**Modern generics only** ``[ruff UP006, UP007, UP035, UP045]``: ``list[X]``,
``dict[K, V]``, ``X | None`` -- never ``typing.Optional``/``List``/``Dict``/
``Tuple``/``Set``/``Union``.

**Mark an override in a plain-Python class hierarchy with ``@typing.override``**
``[review]``. Why: a type checker sees the base there and turns a renamed or
re-signed parent into an error. On an Odoo ``_inherit`` model no checker can see
the parent, so the decorator is not required.

.. code-block:: python

   from typing import override


   class JsonFormatter(logging.Formatter):
       @override
       def format(self, record: logging.LogRecord) -> str:
           ...

2.9.12 Float and currency comparison
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Never compare floats or ``Monetary`` values directly, and never invent an
epsilon** ``[ruff RUF069]`` ``[review]``. Currency amounts use the currency's
methods; other floats use ``odoo.tools`` with ``precision_digits``.

.. code-block:: python

   currency = order.currency_id
   if currency.is_zero(line.price_subtotal):
       ...
   if currency.compare_amounts(paid, total) >= 0:     # paid >= total
       order.state = "paid"
   amount = currency.round(raw_amount)

   from odoo.tools import float_compare
   float_compare(qty, 0.0, precision_digits=3)

``RUF069`` catches only ``==``/``!=`` between inferable floats; ordering and
recordset attributes are review.

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

**Pass logging arguments lazily** ``[ruff G004, RUF065]``.

**Cross-model flows (invoicing, EDI, payments) put a correlation id in every
line** ``[review]``:

.. code-block:: python

   _logger.info("[order:%s] PAC stamping completed, UUID: %s", order.name, uuid)

2.9.14 Background jobs (``ir.job``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Run deferred one-off work as an ``ir.job``** ``[review]`` -- never threads,
``cr.commit()`` loops or OCA ``queue_job``. Crons are for recurring work.

.. code-block:: python

   class StockPicking(models.Model):
       _inherit = "stock.picking"

       @api.job(channel="wms", max_retries=3)
       def _sync_to_wms(self, batch_size=100):
           ...

   # enqueued in the current transaction, executed after commit
   picking.delayed(priority=5, eta=60)._sync_to_wms(batch_size=50)

* Job methods are **private**; ``@api.job`` rejects a public name and the worker
  runs only decorated methods.
* Arguments are **JSON-serialisable**: pass ids, not recordsets or datetimes.
  Target records ride on ``delayed()``'s recordset.
* Bodies are **idempotent**. The job's writes commit atomically with its
  completion; external side effects (HTTP, mail) need their own guards.
* Transient failure: raise ``RetryableJobError(seconds=...)``. Any other exception
  also spends one of ``max_retries``; both roll back. ``TerminalJobError`` fails
  the job without retry.
* Concurrency is capped per **channel** by an ``ir.job.channel`` record
  (``capacity``, default 1). A channel with no record is uncapped. Give heavy
  integrations their own channel record instead of tuning priorities.
* Chain with ``delayed(after=job)``, fan in by passing a union, collapse bursts
  with ``identity_key``. A deferral does not release dependents.
* Defaults: ``channel="root"``, ``priority=10``, ``max_retries=5``,
  ``max_defers=100``. ``idle_timeout=`` (seconds) lets a job's transaction idle
  while it waits on an external party.
* Ops: Settings → Technical → Automation → Background Jobs. Smoke test:
  ``env["ir.job"].delayed()._job_ping()``.

**Not finished is not failed** ``[review]``. When an external dependency is not
ready, call ``self.env["ir.job"]._defer(seconds, reason=...)`` and return: the
job's writes commit, ``retry`` is untouched, and ``identity_key`` stays held.
Deferrals spend ``max_defers``; exhausting it raises ``TerminalJobError``.

.. code-block:: python

   @api.job(channel="sat", max_retries=3, max_defers=24)
   def _poll_remote_package(self):
       self._record_progress()          # kept
       if not self._package_ready():
           self.env["ir.job"]._defer(600, reason="still preparing")

Never use ``RetryableJobError`` for this (it rolls back the progress and spends a
retry), and never re-enqueue from the body (the running job holds its
``identity_key``, so the enqueue is dropped).

2.10 Lazy imports
-----------------

**Import at module level; a function-level import carries a comment naming one
of the reasons below** ``[review]`` (``PLC0415`` is suppressed in ``ruff.toml``).

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

The same lazy import in two functions of one file is promoted to module level.

----

3. XML
======

3.1 Format
----------

**Formatting and ordering are owned by fixers; never hand-align**
``[test_lint test_pretty_xml, test_xml_records]``
``[fixer _pretty_xml, _sort_xml_records]``. Run the sorter first, the formatter
last.

The conventions they enforce:

* ``<?xml version="1.0" encoding="utf-8"?>`` on line 1; 4-space indentation; root
  ``<odoo>``, not ``<data>``.
* Double-quoted attributes; empty elements self-close.
* Attribute order: ``id`` then ``model`` on records; ``name`` first on fields;
  ``menuitem``, ``template``, ``delete``, ``function`` per ``ATTRIB_ORDER`` in
  ``odoo/addons/test_lint/tests/_sort_xml_records.py``.
* Arch attribute order (``ARCH_ATTRIB_ORDER``, same file; HTML untouched):
  identity (``name``/``for``/``expr``, ``position``, ``special``, ``type``) →
  text (``string``, ``placeholder``, ``help``, ``confirm``) → rendering
  (``widget``, ``icon``, ``col``, ``nolabel``, ``optional`` …) → data
  (``domain``, ``context``, ``options``, ``default_order``, ``editable`` …) →
  conditions (``groups``, ``invisible``, ``column_invisible``, ``readonly``,
  ``required``) → ``class``, ``style`` → the rest alphabetically.
* Field order in a record: ``FIELD_ORDER`` (same file), one list per technical
  model -- identity first, large ``arch`` / ``help`` / ``body_html`` last, unlisted
  fields alphabetically after. Every listed name is a field of its model
  ``[test_lint test_fixers]``; a field rename updates the list. Business models
  keep their written order.
* One blank line between top-level records, after ``<odoo>`` and before
  ``</odoo>``.
* 88 columns; a longer tag wraps one attribute per line. A single attribute over
  88 stays on its own line.
* ``domain``, ``context`` and ``options`` values on **one line** (XML normalises
  newlines in attributes).

Static rules ``[test_lint test_xml_lint]`` (``odoo/addons/test_lint/tests/_xml_rules.py``;
each at zero unless ``floors.json`` names it):

* Root is ``<odoo>`` (``data-root``); every data file is in the manifest's
  ``data``/``demo`` or loaded by path from Python (``orphan-data-file``).
* A ``<field name>`` appears once per record (``duplicate-field``).
* ``eval=`` parses and is non-empty (``eval-syntax``); x2many ``eval`` uses
  ``Command.*``, not tuples (``legacy-x2many-command``)
  ``[fixer _modernize_commands]`` -- then run the sorter and formatter.
* Every ``model`` named by a record, view or action exists (``unknown-model``).
* Every install-time reference resolves statically ``[test_lint test_record_refs]``:
  ``ref=``, ``ref()`` in ``eval``/``context``/``search``, ``%(xmlid)d`` in an arch
  or ``<template>``, ``<template inherit_id>``, ``<menuitem parent/action>``,
  ``<delete id>``.

3.2 XML IDs
-----------

**Prefix style: role first, entity second** ``[review]``.

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

Legacy core ids in other shapes (``sale_order_menu``, ``{model}_comp_rule``) are
referenced by their real id, not copied.

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

**Search** -- a ``<group>`` takes no ``string`` or ``expand`` (rejected by
``odoo/addons/base/rng/common.rng``). Every group and filter has a ``name``
(``search-item-name``). A group-by filter has no ``domain``
(``groupby-filter-domain``):

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

**Kanban** -- the card template is ``t-name="card"`` (``kanban-box``); CSS classes
are ``card`` and ``menu``. Each ``t-name`` is its own template scope: a ``t-set``
in ``menu`` is invisible in ``card`` (``kanban-template-scope``):

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

Every view type ``[test_lint test_xml_lint]``:

* ``name=""`` on groups, pages and divs, unique per arch (``duplicate-arch-name``).
* Conditions (``invisible=``, ``readonly=``, ``required=``) are Python expressions
  that parse and are non-empty (``expression-syntax``), spelled ``True``/``False``
  (``boolean-spelling``). No ``attrs=``/``states=`` (``removed-attribute``).
* ``optional=`` is ``show`` or ``hide`` (``optional-value``).
* No dead attributes: ``nolabel=`` outside ``<group>``/``<setting>``
  (``nolabel-outside-group``), ``column_invisible=`` in a form
  (``column-invisible-outside-list``), ``readonly=`` equal to ``invisible=``
  (``readonly-duplicates-invisible``), ``type=`` beside ``special=``
  (``special-button-type``).

3.4 Wizards
-----------

**TransientModel views live in ``wizards/``** ``[review]``, with no ``<sheet>``,
``<header>`` or ``<chatter/>``; buttons go in ``<footer>``.
``res.config.settings`` is a wizard.

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

* **Target by ``name=``, never by position**; the XPath compiles
  (``xpath-syntax``). ``hasclass()`` targets a CSS class.
* Positions: ``inside``, ``after``, ``before``, ``replace``, ``attributes``;
  empty ``replace`` deletes.
* Under ``position="attributes"`` only ``<attribute>`` children are read
  (``attributes-spec-child``).

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

**Output with ``t-out``; never ``t-esc`` or ``t-raw``**
(``deprecated-output-directive``) ``[fixer _modernize_output_directives]``. The
fixer renames ``t-esc``; rewrite ``t-raw`` by hand.

``report_name`` is required. ``binding_type`` is ``"report"`` (Print menu) or
``"action"``; ``binding_view_types`` is order-significant. Localise with
``t-lang=`` on the ``t-call``.

3.6.1 PDF rendering is WeasyPrint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``qweb-pdf`` renders with **WeasyPrint** and CSS Paged Media
(``WeasyPrintEngine``, ``addons/web/models/ir_actions_report.py``). ``web`` owns
every PDF path, ``report.layout``, ``web.minimal_layout`` and
``web.external_layout``. Paged-media CSS:
``addons/web/static/src/webclient/actions/reports/report_paged_media.css`` and
``report_pdf_layout.css``.

**Layout** ``[review]``

* Bootstrap 5 classes only: ``text-end``/``text-start``, ``float-end``,
  ``ms-*``/``me-*`` (``text-right`` fails silently).
* No responsive breakpoints (``col-md-*``); in PDF use CSS Grid
  (``o_report_header_*``, ``o_report_footer_grid``). No ``<table>`` layout.
* Report CSS goes in SCSS added to ``web.report_assets_common``, never inline
  ``<style>`` or ``style=``. Use the design tokens (``--co-primary``,
  ``--co-font``, ``--rp-*``), never hard-coded colours.

**Paperformat** -- set ``format`` / ``page_width`` / ``page_height``,
``margin_*`` (mm), ``orientation``, ``header_line``, ``css_margins``. Never set
``dpi``, ``header_spacing`` or ``disable_shrinking``: they are inert. Header and
footer height come from ``margin_top`` / ``margin_bottom``.

**Paged-media toolbox** -- use these, not hacks:

* Page numbers: ``<span class="page"/>``, ``<span class="topage"/>`` (CSS
  counters, never JavaScript).
* Breaks: ``o_page_break_before`` / ``o_page_break_after``,
  ``break-inside: avoid``, ``o_thead_no_repeat``.
* Outline: ``bookmark-level`` on ``h2[name="document_title"]`` and ``h3[name]``.
* ``string-set`` running headers, ``target-counter()`` with ``leader('.')``,
  named ``@page`` rules, ``float: footnote``.
* PDF/A-3, Factur-X and XMP via ``_prepare_pdf_options``;
  ``data["__pdf_options__"]`` also takes ``dpi`` and ``jpeg_quality``.

**Engine services** (no template work): ``/Title`` from ``print_report_name``,
``/Lang`` (enables ``hyphens: auto``); ``with_context(report_watermark="DRAFT")``;
per-company ``report.theme`` tokens via ``web.styles_company_report``; a failed
render names the offending CSS rule in its ``UserError``.

In test mode ``_render_qweb_pdf`` returns HTML unless ``force_report_rendering``
is set; render tests live in ``addons/web/tests/test_report_rendering.py``.

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
reporting. ``path`` gives the action a readable URL. XML domains use lists and
unquoted ``uid``.

**Every menuitem goes in ``views/<module>_menus.xml``** ``[test_lint test_xml_lint]``
(``menuitem-placement``) ``[fixer _relocate_menus]``. List it in ``data`` after
every file defining an action it names. A record that only binds a menu (an
``ir.actions.client`` with ``params.menu_id``) lives there too; a record patching
``action`` onto a foreign menu becomes the menuitem's ``action=``.

.. code-block:: xml

   <odoo>
     <menuitem id="menu_sale_root" name="Sales" sequence="10"/>
     <menuitem id="menu_sale_order" name="Orders"
               parent="menu_sale_root" action="action_sale_order" sequence="1"/>
   </odoo>

**Contextual (gear) menus.** The gear menu and the *Actions* dropdown share one
grammar, sections in this order. Each section is a ``COG_GROUP`` constant from
``@web/search/cog_menu/cog_menu_group``; a bare number is rejected.

=======================  =============================================================
``COG_GROUP.DATA``       import and export: Import Records, Export All, Export…
``COG_GROUP.RECORD``     the record at hand: Edit Properties…, Duplicate, Archive
``COG_GROUP.APP``        the current app's own features
``COG_GROUP.PRINT``      reports
``COG_GROUP.ACTIONS``    server-bound actions (``binding_model_id``)
``COG_GROUP.INTEGRATE``  send the view elsewhere: Knowledge, Dashboard, Spreadsheet
``COG_GROUP.DANGER``     irreversible, alone and last: Delete
=======================  =============================================================

- Render items with ``CogMenuItem``; declare shared verbs through
  ``prepareStaticActionMenuItems``, never as raw objects.
- Labels are Title Case and end with ``…`` when they open a dialog, wizard or
  picker first ``[test_lint test_contextual_menu]``. No "Print" prefix inside
  Print.
- Order bound actions with ``binding_sequence``; give recurring verbs a
  ``binding_icon``.
- ``isDisplayed``: cheap synchronous checks first, awaited checks last; mobile
  exclusion via ``env.isSmall``.
- Hotkey ``u`` belongs to the gear; no view button claims it
  ``[test_lint test_contextual_menu]``.

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

``noupdate="1"`` means *seed, do not manage*.

**Install writes every record regardless of ``noupdate``** ``[review]``
(``tools/convert.py`` skips only when ``mode != "init"``). A ``pre_init_hook``
that hands a shipped xml id to an existing record therefore hands that record's
fields to the data file for one write. **A data file carries only fields the
module owns**; a field a user may have set on an adopted record belongs in a
``post_init_hook`` that writes only records the module created.

**The stored ``noupdate`` flag is never refreshed** ``[review]``
(``ir.model.data._update_xmlids`` rewrites only ``model``/``res_id``). Changing a
``noupdate`` record in the tree reaches existing databases only through a
**pre**-migration that clears ``ir_model_data.noupdate`` for that xml id; log how
many rows it touched. This is why a renamed method inside a ``noupdate``
``ir.cron`` needs a migration (§2.4.19).

**Neither failure shows on a fresh database.** Verify with ``-u <module>`` on a
restored production copy, after listing which shipped xml ids the database
already has.

----

4. JavaScript
=============

4.1 Modules and files
---------------------

* **Colocate a component's ``.js`` and ``.xml`` in a feature folder**
  (``static/src/<feature>/<component>.js`` + ``.xml``) ``[review]``.
* **ES6 imports only; never ``require()``** ``[review]``.

.. code-block:: javascript

   import { Component } from "@odoo/owl";
   import { registry } from "@web/core/registry";
   import { _t } from "@web/core/translation";

``/** @odoo-module **/`` is a bundler directive, read from the first 500 bytes by
``odoo/tools/assets/esm_graph.py``. Files under ``static/src`` and ``static/tests``
are routed by path; write the directive only for a modifier or a file outside them:

* ``@odoo-module ignore`` -- keep the file out of the ESM pipeline (classic script,
  vendored library).
* ``@odoo-module native`` -- a true native ES module.
* ``@odoo-module alias=<specifier>`` -- register an additional import path.
* ``@odoo-module default=<name>`` -- control default-export bridging.

Both rules below guard failures that serve an HTTP ``200`` with a blank page:

* **Every ``@addon/...`` import resolves to a file** ``[test_lint test_esm_specifiers]``.
  Why: one unresolvable specifier fails the whole esbuild bundle; in a test file
  it silently registers no suite.
* **A bundle rendered by ``t-call-assets`` that carries ES-module sources is
  declared under the manifest's ``esm`` key** ``[test_lint test_esm_bundles]``.
  Why: undeclared, every module file is replaced by a ``console.error`` stub. A
  bundle only ever ``('include', ...)``-ed needs no declaration.

Run both after any move, rename or new bundle::

   odoo-bin -d <db> -i test_lint --test-enable --stop-after-init --no-http \
       --test-tags '/test_lint:TestEsmSpecifiers,/test_lint:TestEsmBundles'

**Under ``--test-enable`` or ``--dev=assets`` a failed esbuild build raises
``EsbuildBundleError``; fix the import or declaration, never silence the bundle**
``[review]``. The ``ir.config_parameter`` ``web.esbuild.fail_closed = 0`` is an
escape hatch for a run that must survive a known-broken bundle, not a fix.

4.2 Naming
----------

* **Components ``PascalCase``; methods and variables ``camelCase``** ``[review]``.
* **A JS string naming a Python method matches it verbatim** ``[review]`` -- an ORM
  call or button ``name`` targeting ``action_view_invoices`` spells exactly that.
* **Portal template ``t-name`` values follow the field naming conventions**
  (``invoice_state``, not ``invoice_status``) ``[review]``.

4.3 OWL
-------

4.3.1 Rules
~~~~~~~~~~~

* **Call ``super.setup()`` first when patching** ``[review]``.
* **Hold reactive state in ``useState``** ``[review]``. A plain assignment does not
  re-render.
* **Verify every import path against the current tree** ``[review]``. Components
  move between releases.
* **POS: ``t-inherit`` for markup, ``patch`` for behaviour; ``onMounted`` DOM access
  only for measurement and focus** ``[review]``. Raw DOM injection breaks on
  re-render.
* **``t-out``, never ``t-esc``, in an OWL template** -- static XML and tagged
  ``xml`` templates in JS alike, inheritance locators, ``<attribute name="t-out">``
  and ``@t-out`` XPaths included ``[test_lint owl_t_esc]``. OWL 3 removes
  ``t-esc``; the vendored OWL 2 (``Agro-Marin/owl`` ``2.8-marin``) renders a
  non-block object through ``t-out`` as its string, as ``t-esc`` did. Two
  differences remain: a ``markup()`` value renders as HTML, and a body default
  replaces ``null``/``undefined`` but not ``false``. View archs are compiled by
  the view compilers and still accept ``t-esc``.
* **Name every component member ``this.x`` in a template**, and pass a
  ``t-call``'s values as attributes (``<t t-call="x" value="1"/>``), not as
  ``t-set`` children. OWL 3 resolves a bare name only among the template's own
  locals (``t-set``, ``t-foreach``/``t-as``, ``t-slot-scope``, arrow
  parameters); a template called with ``t-call-context`` reads that context as
  ``this``. ``[review]``; ``this_scope.py --check`` (``Agro-Marin/owl``
  ``tools/odoo_migration``), run over odoo, enterprise and agromarin together,
  must change 0 files. A template rendered without a component
  (``renderToString``, ``renderToElement``, ``renderAt``) keeps bare names.
  A getter or method the template calls reads component state only; a value
  the template holds -- a ``t-as`` item, a ``t-set``, a slot scope -- is an
  argument (``this.isActive(workcenter)``), because ``this.x`` runs the member
  on the component, not on the render context a bare ``x`` used to lend it
  (§4.3.2).

4.3.2 ``this`` in a template is not always the component
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OWL renders against a derived context
(``addons/web/static/lib/owl/owl.es.js``)::

   const ctx = Object.assign(Object.create(this.component), { this: this.component });

Reads resolve through the prototype; a write to a bare instance property lands on
the throwaway ``ctx`` and is lost.

.. list-table::
   :header-rows: 1

   * - Reference in the template
     - ``this`` inside the member
     - Bare ``this.x = …``
   * - ``this.foo()``
     - the component
     - safe
   * - ``t-on-click="foo"``
     - the component (``handler.call(node.component, ev)``)
     - safe
   * - ``onFoo.bind="foo"``
     - the component
     - safe
   * - ``foo`` / ``foo.bar`` (bare getter or method)
     - the derived ``ctx``
     - **lost**

**A bare template getter or method never rebinds an instance property; it mutates a
container created in ``setup()``** ``[review]`` (see
``Many2XAutocomplete.emptySearchMemo``). ``this.obj.key = v`` is safe;
``this.counter = 1`` is lost. A member reached transitively binds like its entry
point.

4.3.3 Patching
~~~~~~~~~~~~~~

.. code-block:: javascript

   patch(ProductCard.prototype, {
       setup() {
           super.setup(); // always first
           this.orm = useService("orm");
           this.customState = useState({ data: null });
           onWillStart(async () => {
               this.customState.data = await this.orm.call("product.product", "custom_read", []);
           });
       },
   });

.. code-block::

   Change an existing component's markup?  -> t-inherit the template
   Change its behaviour?                    -> patch(Component.prototype, {...})
   New UI element?                          -> new OWL component + registry entry

4.4 Tests
---------

**Every frontend change ships with a test** ``[review]``. **Never write QUnit** --
it is removed.

* **Unit and component: Hoot** -- ``static/tests/**/*.test.js``, importing
  ``@odoo/hoot`` / ``@odoo/hoot-dom``, mock server for ORM calls. The default.

  .. code-block:: javascript

     test("counter increments on click", async () => {
         await click("button.increment");
         expect("span.value").toHaveText("1");
     });

* **Integration and end-to-end: tours** -- registered in ``web_tour.tours``, driven
  by an ``HttpCase`` tagged ``@tagged("post_install", "-at_install")`` via
  ``self.start_tour(url, "tour_name", login=...)``.

Runner facts:

* **Restart the server after every change before a Hoot run.** The unit-test bundle
  is not rebuilt while the server runs (XML, new ``.test.js``, plain edits alike).
* **Read the import-failure line, not "Passed N".** An import failure shows only as
  a lower pass count.

**ESLint and ``tsc`` report zero findings** ``[review]``; ``./gates.sh --js`` fails on
any.

----

5. CSS / SCSS
=============

5.1 Naming and organisation
---------------------------

* **Prefix classes with the module: ``.o_module_name_element``** ``[review]``.
* **Put files in ``static/src/scss/`` or beside the component they style**
  ``[review]``.
* **Declare each file under the manifest's ``assets`` in the bundle that loads
  where the style is needed** ``[review]``. Wrong-bundle CSS does nothing or bloats
  every page.

.. list-table::
   :header-rows: 1

   * - Bundle
     - Loads in
   * - ``web.assets_backend``
     - backend web client
   * - ``web.assets_frontend``
     - website and portal
   * - ``point_of_sale._assets_pos``
     - Point of Sale client
   * - ``web.report_assets_common``
     - QWeb PDF reports
   * - ``web._assets_primary_variables``
     - SCSS variable overrides, loaded first; emits no rules

5.2 Theming
-----------

* **Reuse Bootstrap 5 utilities and components before writing SCSS** ``[review]``.
* **Never hard-code a colour or spacing a variable controls; override the Odoo or
  Bootstrap variable in ``web._assets_primary_variables`` /
  ``_secondary_variables``** ``[review]``.
* **Dark overrides go in a ``*.dark.scss`` sibling**, globbed into
  ``web.assets_web_dark`` / ``web.assets_backend_dark`` ``[test_lint test_dark_sibling_scope]``.
* **Use logical properties (``margin-inline-start``) and Odoo's RTL-aware mixins,
  never hard ``left`` / ``right``** ``[review]``. RTL is generated.

5.3 Browser floor
-----------------

**Target current evergreen browsers only; no declaration carries an old-browser
fallback** ``[review]``. JS floor: ``_ESBUILD_TARGET = "es2023"`` in
``odoo/tools/assets/esbuild.py``. CSS: anything Baseline *newly available* is
allowed in every bundle, public ones included.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Use
     - Instead of
   * - ``color-mix(in srgb, C N%, transparent)``
     - ``rgba($c, .N)``
   * - ``hsl(from C h s calc(l - 10))``
     - ``darken($c, 10%)`` -- exact equivalent
   * - ``light-dark(a, b)``
     - a one-off colour that differs by scheme and deserves no token
   * - ``oklch(from C calc(l - .1) c h)``
     - a *deliberate* perceptual palette change; does **not** reproduce ``darken()``

**Prefer a CSS colour function to a Sass one** ``[test_lint test_scheme_duplication]``.
Why: Sass resolves at compile time, forcing one stylesheet per scheme; CSS resolves
in the cascade and answers both.

**Keep contrast picks compile-time, per scheme, via ``o-scheme-contrast()``; never
``contrast-color()``** ``[review]``. Why: ``contrast-color()`` returns only white or
black.

5.4 Moving a variable onto a token
----------------------------------

``o-token(--name, $fallback)`` turns a Sass assignment into a ``var()``. **Never
tokenise a variable that** ``[review]``:

* **is read by Sass colour maths** (``darken()``, ``mix()``, ``rgba()``,
  ``color-contrast()``…) -- the compile fails with ``is not a color``. Grep the
  whole workspace first: ``$card-bg`` is read in ``portal``.
* **is interpolated into an SVG data URI** (``$form-check-*-color``)
  ``[test_lint test_scheme_duplication]`` -- the ``var()`` is inert there and the
  icon silently disappears. Convert it only together with the image.
* **is passed to a mixin written for colours.** ``o-button-variant-from()`` and
  ``o-print-color-rgb()`` accept tokens; others fail.

5.5 Restating a rule for the other scheme
-----------------------------------------

Where neither a token nor ``light-dark()`` can carry a value, restate the rule under
``:root[data-color-scheme="dark"]`` (specificity 0,2,0) in ``scheme_rules.scss`` or
``html_editor.scheme_rules.scss`` ``[review]``:

* **One scoped rule per original rule, with its whole selector list, copied as the
  bundle emits it.**
* **Only the dark half.**
* **Screen only.** ``assets_web_print`` includes the backend bundle unconditionally.
* **Never in a file riding ``assets_frontend``**; split a sibling declared in the
  backend bundle alone (as ``html_editor.scheme_rules.scss``).
* **Never call ``tint-color()`` / ``shade-color()`` in a scoped block; use
  ``o-scheme-tint(…, $-scheme)`` / ``o-scheme-shade(…, $-scheme)``.** Why:
  ``bs_functions_overridden.dark.scss`` redefines both for dark, so the two bundles
  disagree.
* **No ``@extend`` in a scoped block** unless the placeholder emits no colour, in
  which case omit it from the dark half (see ``o-bg-color()``'s
  ``$extend-heading-reset``).

5.6 Weighing a conversion
-------------------------

**Drop a token conversion that reduces neither compiled bundle size nor
``TestSchemeDuplication``'s count** ``[review]``. A ``var(--name, <fallback>)`` is
longer than the colour it replaces, per use.

----

6. Tests
========

6.0 Choosing a tier
-------------------

**Use the lightest tier that can express the test** ``[review]``. §6.1 onwards
concerns Tier 3.

.. list-table::
   :header-rows: 1
   :widths: 16 34 50

   * - Tier
     - Entry point
     - Use when
   * - **1 -- Component**
     - ``odoo/orm/components/tests/`` and the other ``pytest.ini`` ``testpaths``
     - ORM algorithms in isolation (cache, compute scheduling, flush, trigger
       graph) against the real component objects. No fields, no ``odoo`` imports.
   * - **2 -- ORM, database-free**
     - ``model_test_env`` / ``ModelRegistry`` (``odoo/orm/model_test_env.py``);
       ``InMemoryCase`` (``odoo/tests/in_memory_case.py``) for an addon class
     - Real model methods, ``@api.depends`` computes and ``Field`` descriptors
       against an in-memory backend. No PostgreSQL.
   * - **3 -- Integration**
     - ``TransactionCase`` / ``HttpCase``
     - SQL, ACLs, several modules, or the web client.

Tier 1's hand-rolled dependency graph is the subject under test; not reusing
Tier 2's ORM is intentional.

These tiers are not ``pytest.ini``'s "Tier 1 / Tier 2" *invocation groups*
(CLAUDE.md §8), which split pytest runs by stubbing, not by test weight.

**Run the pytest suites as two invocations from the ``odoo/`` checkout, passing all
six real-import paths** ``[review]``; ``./gates.sh`` runs both. Why: the first registers
process-global ``sys.modules`` stubs that shadow the second's imports, and a
shorter path list silently skips suites.

.. code-block:: bash

   pytest                                          # stubbed (pytest.ini testpaths)
   pytest odoo/orm/tests odoo/http/tests odoo/db/tests odoo/tools/tests \
       tests/service tests/framework               # real imports

``tests/framework`` asserts facts about the real ``odoo.*`` packages (façade
``__all__``, monkeypatch application); it cannot run stubbed.

Real-resource suites, run only when named:

.. code-block:: bash

   ODOO_CONTRACT_REQUIRE_DEPS=1 pytest tests/contract  # PostgreSQL + psql/pg_dump
   pytest tests/process    # boots real odoo-bin processes
   pytest tests/loading    # installs base into a scratch DB
   pytest tests/perf       # statement-count and time floors

* **Write a contract test whenever code branches on how a dependency behaves,
  asserting the dependency directly** ``[review]``. Why: a mock encodes the same
  belief as the code. **Run ``tests/contract`` with
  ``ODOO_CONTRACT_REQUIRE_DEPS=1``**; without it a missing dependency passes.
* **Add a process test only for behaviour that vanishes when anything is mocked;
  assert only observables** (port, process tree, HTTP response) ``[review]``.
* **Readiness is a served request, never a log line** ``[review]``. Why:
  ``ThreadedServer.run`` logs "HTTP service running" before
  ``preload_registries``, so requests still block.

6.1 Layout and base classes
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Base class
     - Use for
   * - ``TransactionCase``
     - standard ORM tests; each method rolled back
   * - ``SingleTransactionCase``
     - tests deliberately sharing state across methods
   * - ``HttpCase``
     - controllers, web UI, headless Chrome; ``@tagged("post_install", "-at_install")``

**Every file in ``tests/`` is imported exactly once from ``tests/__init__.py``**
``[test_lint test_test_holes]``. An unimported file never runs.

.. code-block::

   tests/
     __init__.py          # from . import test_sale_order, test_sale_order_line
     test_sale_order.py
     test_sale_order_line.py

**Naming: files ``test_<feature>.py``, classes ``TestFeatureName``, methods
``test_<specific_scenario>``** ``[review]``.

6.2 Isolation
-------------

* **Create fixtures in ``setUpClass()``; use ``setUp()`` only when a method mutates
  shared state** ``[review]``.
* **Freeze time with ``odoo.tests.freeze_time``; never depend on
  ``datetime.now()``** ``[review]``.
* **Mock every external service; tests run offline** ``[review]``.
* **Run as a user holding only the group under test; ``@users(...)`` for
  multi-user cases** ``[review]``.
* **A fixture that reuses a shipped record sets every field it relies on**
  ``[review]``. Why: demo data may have reconfigured it (e.g. an approval category's
  ``approval_minimum`` and ``approve_sequentially``), so a suite green without demo
  goes red with it. The same holds for logins (create unique ones) and time windows
  (create the records under test as your own user, not the superuser).
* **Never call ``cr.commit()``** ``[review]``. Exception: a concurrency or cron test
  that opens ``self.registry.cursor()`` deliberately.
* **Tag a test class exactly one of ``at_install`` / ``post_install``** ``[review]``.
  Pure ORM tests are ``at_install``; anything touching other modules, the web client
  or tours is ``post_install``. ``@tagged`` only warns on a violation.

.. code-block:: python

   @classmethod
   def setUpClass(cls):
       super().setUpClass()
       cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})

6.3 ``BaseCommon``
------------------

``odoo.addons.base.tests.common.BaseCommon``: a ``TransactionCase`` with mail and
tracking disabled. **Use it when mail noise is irrelevant** ``[review]``.

Provides ``DISABLED_MAIL_CONTEXT``; ``cls.company``, ``cls.currency``,
``cls.partner``; ``cls.group_user`` / ``cls.group_portal`` / ``cls.group_system``;
``quick_ref(xmlid)``, ``_create_partner()``, ``_create_new_internal_user()``,
``_create_new_portal_user()``. ``setup_independent_user`` /
``setup_independent_company`` return ``None`` unless overridden.

6.4 Structure and completeness
------------------------------

**Structure each test as setup → action → assertion, separated by blank lines**
``[review]``.

.. code-block:: python

   def test_order_confirmation_sets_date(self):
       order = self.env["sale.order"].create({
           "partner_id": self.partner.id,
           "order_line": [Command.create({"product_id": self.product.id})],
       })

       order.action_confirm()

       self.assertEqual(order.state, "sale")
       self.assertTrue(order.date_order)

* **Use the most specific assertion** (``assertEqual``, ``assertIn``,
  ``assertRaises``) ``[review]``.
* **``assertRaises`` names the specific exception class, never ``Exception``**
  ``[ruff B017]``.
* **Every test class covers at least one expected-failure path**
  (``ValidationError``, ``AccessError``, refused transition) ``[review]``.
* **Parameterise with ``subTest()``** ``[review]``:

  .. code-block:: python

     for amount, rate, expected in cases:
         with self.subTest(amount=amount, rate=rate):
             self.assertAlmostEqual(compute(amount, rate), expected, places=2)

* **Test onchange with ``odoo.tests.Form``** ``[review]``.
* **Lock hot paths with ``assertQueryCount``** (``@warmup`` primes caches)
  ``[review]``.
* **Pin the shape before the number** ``[review]``:
  ``self.assertQueriesConstant(run, small=2, large=40)`` fails when a batch's count
  grows with its size. Keep an absolute pin beside it for the constant.
* **Before moving a query-count pin, get the stack of the extra (or missing)
  calls; the commit states what each unit bought** ``[review]``. Why: work that
  *moves* changes the count as readily as work that grows.
* **Pin the guarantee, not the arithmetic: assert a bound, then the mechanism**
  ``[review]``. Do: ``assertLessEqual(compiles, 1)``, then a second render asserting
  zero. Don't: ``assertEqual(compiles, 1)``. A bound alone is satisfied by the work
  not happening at all.

6.5 Raw SQL in tests
--------------------

**Flush before asserting on database state** ``[review]``:

.. code-block:: python

   self.order.write({"state": "sale"})
   self.order.flush_recordset(["state"])
   self.env.cr.execute("SELECT state FROM sale_order WHERE id = %s", (self.order.id,))
   self.assertEqual(self.env.cr.fetchone()[0], "sale")

6.6 Lint relaxations in tests
-----------------------------

**Tests do not relax ``B017`` (§6.4), ``S113`` (every HTTP call passes a timeout)
or ``T201`` (no ``print``; log instead)** ``[ruff]``; ``ruff.toml``'s ``**/tests/**``
entry must not list them. That entry is the authority for the rest: ``RUF015``, ``PLW0603``,
``PLR6201``, ``S110``, ``TRY002``, ``TRY203``, ``EM101``, ``PLR0124``, ``A001`` /
``A002``, ``RUF069``, ``FURB152`` (fixture floats are not π), ``B018`` / ``B015``
(a field touch or ``in`` under ``assertRaises`` is the assertion), ``RUF075``
(post-``yield`` code is the assertion).

``ANN``, ``ARG``, ``FBT003``, ``RUF012`` and ``S301`` are exempt in
``odoo/libs/**/tests/**`` and ``odoo/orm/components/**/tests/**``.

6.7 Tagging
-----------

* Default: ``standard`` + ``at_install``. ``HttpCase``:
  ``@tagged("post_install", "-at_install")``.
* **An ``at_install`` test must pass both at install and when deferred**
  ``[review]``. On a database where a dependent is already installed, the loader
  defers the suite until those dependents load and logs
  ``Module <m>: N at_install test(s) deferred until …``. A failure only when
  deferred is a real interaction with a dependent: fix it.
* **Exclude slow or external tests with ``@tagged("-standard")``, optionally plus
  ``external`` or ``nightly``; there is no ``heavy`` tag** ``[review]``.
* **Localisation tests carry exactly one of ``post_install_l10n`` /
  ``external_l10n``, each with its base tag** ``[test_lint test_l10n]``.
* **Tag a HOOT test ``desktop``, ``mobile`` or ``headless``** via
  ``test.tags(...)`` or file-level ``describe.current.tags(...)`` ``[review]``.
  DOM-free (no mount, no ``@odoo/hoot-dom``) is ``headless``; viewport- or
  touch-dependent is ``desktop`` / ``mobile``. Why: an untagged test runs in both
  passes, so a DOM-free one runs twice for nothing. ``headless`` still runs in
  the desktop pass.

6.8 Coverage
------------

**Every ``action_*`` method, constraint and validation has a test; cover edge
cases** ``[review]``.

.. code-block:: bash

   odoo-bin -d <db> -i <module> --test-enable --test-tags /<module> --stop-after-init
   odoo-bin -d <db> --test-enable --test-tags /<module>:TestClass.test_method --stop-after-init
   odoo-bin -d <db> -i <module> --test-enable --test-tags post_install --stop-after-init
   coverage run odoo-bin -d <db> -i <module> --test-enable --test-tags /<module> --stop-after-init
   coverage report

* **Capture server output with ``>>``, ``tee`` or ``--logfile``, never ``>``**.
  Why: Odoo writes from several descriptors without ``O_APPEND``.
* **Gate on the exit code plus the ``N failed, M error(s) of T tests`` summary.**
* **Stopping a backgrounded run kills only the shell; kill ``odoo-bin`` by PID.**

6.9 Pre-existing failures
-------------------------

**Decide whether a failure is pre-existing by diffing failure names against the same
suite at ``HEAD`` in a detached worktree** (``./gates.sh --ref HEAD`` or
``git worktree add --detach``) ``[review]``. Never re-run to guess.

* **Never count failures by grepping ``ERROR``** ``[review]``. PostgreSQL error text
  appears in passing tests' logs. Anchor on
  ``<ts> <pid> ERROR uid:... <logger>: FAIL|ERROR: <Class.method>`` or the
  ``N failed, M error(s) of T tests`` summary.
* **Diff failure names, never counts** ``[review]``. One fix plus one new break
  leaves the count unchanged.

----

7. Git
======

7.1 Commits
-----------

**Subject: ``[TAG] scope, scope, …: lowercase summary``** ``[review]``.

* ``scope`` is a module, a core package or path (``orm``, ``doc/architecture``,
  ``CLAUDE.md``), or a comma-separated list of them. A long list collapses to
  ``x, y, z and N more``.
* The summary states the resulting behaviour in lowercase prose; a second clause
  ``, and …`` is normal.
* No length cap. Do not truncate; ~90–130 characters is typical.

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

**One tag per commit, by dominant intent; split a commit with two intents**
``[review]``. ``LINT`` and ``CLN`` contain no behaviour change; if they do, the tag
is ``REF``.

**Body: prose** ``[review]`` -- the concrete defect (call sites, wrong behaviour),
what changed and why, and the consequences. One finding per paragraph, optionally
led by a bare-caps sentence. Numbers go in an indented ``before -> after`` block.

**Trailers: ``Verification:`` with the commands run and raw numbers; ``Task ID: <n>``
when the work belongs to a ``project.task``** ``[review]``. Never invent a task id.
No ``Solution:`` block.

.. code-block::

   [REF] base, account, website_sale and 60 more: res.partner.bank_ids becomes bank_account_ids, and t-foreach joins the attributes a rename rewrites

   The field is a One2many of res.partner.bank.account and was labelled
   "Banks", which is res.bank, a different model.

       res.partner.bank_ids          -> bank_account_ids
       base.document.layout.bank_ids -> bank_account_ids

   AND THE RENAME FOUND A HOLE IN THE RENAMING TOOL. t-foreach was not in
   _EXPRESSION_ATTRIBUTES, so three report arches would have kept the old name.

   Verification:
       install at HEAD then upgrade    fields 2/2 renamed, views 5 -> 0

**In a shared checkout commit with an explicit pathspec:
``git commit -F <msgfile> -- <file> …``** ``[review]``. It records those paths'
working tree regardless of the shared index.

**Name files in the pathspec, never a directory** ``[review]``. A directory pathspec
records every deletion under it:

.. code-block::

   rm research/note.md
   git commit -F msg -- research/keep.md    # note.md survives
   git commit -F msg -- research            # note.md deleted, unmentioned

Read ``git status`` for ``D`` lines before and after committing.

7.2 Branches and task IDs
-------------------------

**Branches are topic-slugged: ``19.0-<topic>[-<developer>]``, e.g.
``19.0-documents-web-framework-maringuadarrama``** ``[review]``. No task IDs in
branch names or commits; never invent one.

**Never commit to ``19.0``** -- the pristine upstream mirror. ``19.0-marin`` is the
integration branch; work lands there, directly or via a topic branch cut from it.
The same model applies to the fork's other upstream mirrors.

7.3 Pull requests
-----------------

A PR is the route that gets review; **it is not required** for work its author owns
end to end. The knowledge repository works directly on ``main``.

* **Title: the commit subject shape of §7.1**; for a single-commit PR, the subject
  itself.
* **Body: the §7.1 body and ``Verification:``**, plus ``EXPLAIN ANALYZE`` output for
  new raw SQL (§11.6) and a screenshot or GIF for UI changes ``[review]``.
* **One commit per logical unit; never squash unrelated changes** ``[review]``.
* **No merge commits from the base branch; rebase instead** ``[review]``.
* **Never force-push a shared branch** (``main``, ``19.0``, ``19.0-marin``,
  ``19.0-prod``); force-push your own topic branch freely ``[review]``.
* **Never push to ``19.0`` / ``19.0-marin`` without explicit confirmation**
  ``[review]``. A push to ``19.0-marin`` runs ``.github/workflows/gates.yml``.

PRs land by **rebase merge**, rewriting every SHA. Afterwards confirm
``git diff <local> origin/<branch>`` is empty, then
``git reset --keep origin/<branch>`` -- never ``--hard``, which destroys
uncommitted work.

----

8. Translations
===============

8.1 Python
----------

**Translate with ``self.env._()``; never import or call the bare ``_()``**
``[review]``. Why: ``_()`` walks the stack with ``inspect.currentframe()`` to infer
language and module -- slower, and wrong under decorators, comprehensions and
callbacks.

.. code-block:: python

   raise UserError(self.env._("Order %s cannot be confirmed.", order.name))

Enforced by ``_checker_gettext`` for both forms (ruff's ``INT`` rules see only bare
``_()``):

* **The first argument is a literal string** ``[test_lint E8502]``.
* **Two or more placeholders are named** ``[test_lint E8503]``:
  ``self.env._("%(done)s of %(total)s", done=x, total=y)``.
* **No ``%r``** ``[test_lint E8504]``.
* **User-facing exceptions take a translated message** ``[test_lint E8505]`` (§2.7).

**For constants outside a method, use ``LazyTranslate``** ``[review]``:

.. code-block:: python

   from odoo.tools import LazyTranslate

   _lt = LazyTranslate(__name__)
   STATES = [("draft", _lt("Draft")), ("done", _lt("Done"))]

8.2 JavaScript and templates
----------------------------

.. code-block:: javascript

   import { _t } from "@web/core/translation";

   const message = _t("Operation completed");

**Keep user-facing literals literal; never assemble one at runtime**
``[test_lint test_i18n, test_jstranslate]``. Only static strings are extracted.

**A module with JS translations registers itself** ``[review]``:

.. code-block:: python

   class IrHttp(models.AbstractModel):
       _inherit = "ir.http"

       @classmethod
       def _get_translation_frontend_modules_name(cls):
           return super()._get_translation_frontend_modules_name() + ["my_module"]

8.3 ``.pot`` / ``.po``
----------------------

**Template at ``i18n/<module>.pot``, languages at ``i18n/<lang>.po``; re-export
after adding, changing or deleting a user-facing string** ``[review]``:

.. code-block:: bash

   odoo-bin --addons-path=odoo/addons,addons i18n export -d <db> <module>

* **Export through the community trees only** ``[review]``. The header records
  ``odoo.release.series`` (``Odoo Server 19.0``), not ``release.version``
  (``19.0+e``).
* **Never hand-edit a ``msgid``; change the source and re-export** ``[review]``.
* **No duplicate entries in a ``.pot``** ``[test_lint test_pofile]``.
* **Do not commit machine-merged ``.po`` churn that fights Weblate**
  (``.weblate.json``) ``[review]``.

----

9. Code review checklist
========================

What tooling cannot check. Do not re-verify lint codes by hand; skip an item that
does not apply, with a note.

**Security**

#. Dynamic SQL is parameterised or wrapped in ``SQL()`` -- identifiers from ORM
   metadata included.
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
#. Overrides in plain-Python class hierarchies carry ``@typing.override`` (§2.9.11).

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
#. Comprehensions use at most one ``for`` and one ``if``.
#. New code matches ``ruff format``'s style without reformatting the rest of the
   file (§2.1).

**Cyclomatic complexity stays at or under 20 (``[lint.mccabe] max-complexity``)**
``[ruff C901]``. ``ruff.toml`` currently ignores ``C901`` in the main run; check
with ``ruff check <path> --select C901``.

----

10. Security
============

10.1 Method visibility
----------------------

A public method (no leading underscore) is callable over RPC by any
authenticated user, and it enforces no ACL on its own.

* **Make every method private by default** ``[review]``. Drop the underscore only
  for a method that is deliberately an RPC entry point.
* **Mark a method that keeps a public name with ``@api.private``** ``[review]``.
  The RPC boundary checks it across the whole MRO, so a subclass cannot
  re-expose the method. New code uses ``_``. ``@api.private`` is for retrofits.

10.2 ``sudo()``
---------------

* **Escalate as narrowly as possible** ``[review]``. ``with_user()`` and
  ``with_company()`` keep ACLs and record rules enforced. Use ``sudo()`` only for
  cross-tenant or system operations.
* **Whitelist fields before ``sudo().write(payload)`` on user input**
  ``[review]``.
* **Keep sudo scope minimal** ``[review]``: the smallest recordset and the fewest
  operations.

.. code-block:: python

   allowed = {"description", "tag_ids"}
   self.sudo().write({k: v for k, v in values.items() if k in allowed})

10.3 Input validation
---------------------

**Guard security-sensitive logic with ``if`` / ``raise``, never ``assert``**
``[review]``. ``python -O`` strips ``assert``, and ruff ``S101`` is disabled
because the ORM uses ``assert`` for invariants.

.. code-block:: python

   if access_mode not in ("read", "write", "create", "unlink"):
       raise ValueError(f"Invalid access mode: {access_mode!r}")

10.4 SQL injection
------------------

**Pass every dynamic value as a parameter or through ``SQL``**
``[test_lint E8501]``. f-strings, ``.format()`` and ``%`` on a query string are
violations, even when the value is ORM metadata such as ``_table`` or
``field.name``. Ruff ``S608`` is disabled. E8501 tracks constants across
assignments and calls, and it trusts underscore-prefixed attributes such as
``self._table``.

.. code-block:: python

   from odoo.tools import SQL

   self.env.cr.execute("SELECT id FROM res_partner WHERE name = %s", (name,))
   self.env.cr.execute(SQL(
       "SELECT id FROM %s WHERE %s = %s",
       SQL.identifier(model._table), SQL.identifier(field.name), value,
   ))

**Never bind a parameter where PostgreSQL parses syntax**
``[test_lint E8534]``. psycopg 3 binds server-side, so each ``%s`` reaches the
server as ``$N``. As a result, ``IN %s`` and ``INTERVAL %s`` are syntax errors
for every value.

* Write membership as ``= ANY(%s)`` with a **list**. A tuple there fails with
  ``malformed array literal``.
* Or write ``IN %s`` inside ``SQL()`` with a **tuple**. ``SQL`` expands a tuple to
  ``(%s, %s, …)``, and an empty tuple to ``(NULL)``.
* For an interval, pass a ``timedelta`` or use ``SQL.literal``.

.. code-block:: python

   # Don't
   cr.execute("SELECT id FROM res_partner WHERE id IN %s", (tuple(ids),))
   # Do
   cr.execute("SELECT id FROM res_partner WHERE id = ANY(%s)", [list(ids)])
   cr.execute(SQL("SELECT id FROM res_partner WHERE id IN %s", tuple(ids)))

10.5 Related fields and ACLs
----------------------------

**A related field into a sensitive model sets ``compute_sudo=False``, carries
``groups=``, or becomes an ACL-respecting compute** ``[review]``. Related fields
default to ``compute_sudo=True``, so they read as superuser and bypass the
reader's ACLs and record rules. Plain computes default to
``compute_sudo=store``.

**A ``_search`` override that narrows visibility declares
``_search_visibility_fields``** ``[review]``. This is the tuple of fields the
override reads, for example ``ir.attachment``: ``res_model``, ``res_id``,
``res_field``, ``public``, ``create_uid``. Why: the per-scope x2many cache evicts
on writes to the fields a rule tests, and a Python rule is invisible to it.
Declaring nothing means "every field": correct, but it refetches on every write.
``base/tests/test_x2many_cache_scope.py`` checks that each declared name is a
field.

10.6 Controllers
----------------

* **Validate, schema-check and rate-limit every parameter of an
  ``auth="public"`` route** ``[review]``. Unauthenticated visitors reach it.
* **Keep ``auth="none"`` for framework routes** ``[review]``. These routes have
  no database access.
* **Scope and validate ``auth="bearer"`` tokens, and never log them**
  ``[review]``.
* **Never interpolate user input into ``Markup()``** ``[review]``. That includes
  f-strings. Escape user content, and use ``Markup()`` only for intentional HTML.
* **A ``type="http"`` route with ``csrf=False`` authenticates the caller another
  way, and a comment on the decorator names that way** ``[review]``. Valid ways
  are a bearer token, ``auth="receiver"``, or a verified signature. ``jsonrpc`` is
  CSRF-exempt by design.

10.7 Constraints run privileged
-------------------------------

**``@api.constrains`` methods run as ``sudo()`` by default** (fork deviation).

* **Hold constraint bodies to §10.2** ``[review]``. Their reads never raise
  ``AccessError``, and their writes run privileged.
* **Pass ``@api.constrains(..., sudo=False)`` when the check must see the
  current user's view of the data** ``[review]``.
* **Keep a callable spec (``@api.constrains(lambda self: ...)``) independent of
  the env** ``[review]``. It is resolved once per registry class and memoised.

10.8 Access control
-------------------

**Every new model ships explicit access rules** ``[review]``. A model with no
``ir.model.access`` line is inaccessible or silently admin-only.

* **Grant the minimum ACL per (model, group) in
  ``security/ir.model.access.csv``** ``[review]``. A user group typically gets
  ``1,1,1,0`` and a manager group ``1,1,1,1``. **Never ship a group-less line.**
  It grants every user, portal and public included. To grant portal or public
  access, name ``base.group_portal`` / ``base.group_public``.
* **Use record rules (``ir.rule``) when access depends on the record's data**
  (owner, company, state) ``[review]``.

  - A rule with no groups is global: it is AND-ed with every other rule.
  - A rule with groups is ``composition="grant"`` by default. It is OR-ed with
    the user's other grant rules, so it can only widen access. Adding one
    silently disarms the restriction of every other grant rule for that group.
  - **A rule that narrows a group's access declares ``composition="restrict"``.**
    It is AND-ed for the group's members only, and no grant rule can widen it.
  - Set ``perm_*`` to the modes the rule governs. With all four set, the rule
    also governs creation, including records the ORM creates on the user's
    behalf.

* **Write multi-company rules as
  ``[("company_id", "in", company_ids + [False])]``** ``[review]``. Pair them with
  ``check_company=True`` on relational fields (§2.9.10).
* **Restrict sensitive fields with ``groups="module.group_xxx"``** ``[review]``.
  It is enforced on read and write, and it hides the field from every view.
* **Gate a field that everyone reads and only some may change with
  ``write_groups=``, never a computed flag feeding ``readonly=`` in the arch**
  ``[review]``. ``readonly`` is a rendering hint that ``web_save``, import and RPC
  bypass. ``write_groups`` takes the ``groups`` grammar (including ``!`` and
  ``fields.NO_ACCESS``) or a callable on the written recordset. It raises on
  ``write`` and ``create``, and ``fields_get`` reports the field readonly.
  **Delete the node's ``readonly`` attribute when converting.** An explicit arch
  ``readonly`` replaces the server's verdict.
* **Gate a decision, not a structural attribute** ``[review]``. ``write_groups``
  also refuses ``create``, including ``default_*`` context keys. Gating a field
  that every creator must supply (price, category, type, company) blocks ordinary
  creation. Gate decisions reserved to a group (cost, published flag, customer
  flag). Leave the rest as a view-level ``readonly``.
* **Spell every group reference so it resolves** ``[test_lint test_group_refs]``.
  An unknown external id reads as "not a member". ``groups="module.typo"`` then
  hides the node from everyone, and ``groups="!module.typo"`` shows it to
  everyone. A reference into a module this checkout does not carry is left alone
  (optional-dependency idiom).
* **A read-only tier is the lowest rung of its privilege** ``[review]``.
  ``group_<app>_readonly`` (in ``account``, ``stock``, ``sale``, ``purchase``,
  ``mrp``) has sequence 5 or 10, sets ``privilege_id``, and implies
  ``base.group_user``. It must satisfy three invariants:

  - It reads every model the app shows and writes none (``grants_write``).
  - Where a rung of the same privilege narrows a model by record rule, it carries
    its own read rule (``ruleless``).
  - It duplicates no read that ``base.group_user`` already holds through the
    row's dependency closure (``dead_rows``).

  Record rules OR across groups, so the rung that implies the tier is the lowest
  one that already sees every document. An affordance the tier must reach is
  gated ``groups="<transacting rung>,<tier>"``. Each app ships
  ``tests/test_group_readonly.py``, which checks the rung, the implication and
  ``grants_write``. ``ruleless`` and ``dead_rows`` are review. A new app with a
  tier copies the rule and ships the test.

10.9 Configuration and secrets
------------------------------

* **Never hard-code URLs, credentials or endpoints** ``[review]``. Read them from
  ``ir.config_parameter`` or ``odoo.conf``.
* **Namespace config keys as ``<module>.<setting>``** ``[review]``. Read them
  with ``self.env["ir.config_parameter"].sudo().get_param(key, default)``.
* **Store a secret in ``credential.credential`` and hold a Many2one to it**
  ``[test_lint E8520]``. A plain column or an ``ir.config_parameter`` sits in
  every backup in clear text.
* **Hand a secret to a child process in its own ``env=`` mapping, never through
  ``os.environ``** ``[test_lint E8519]``.
* **Declare external dependencies in ``__manifest__.py`` and pin them in
  ``requirements.txt``** (§1.2).

10.10 Deployment checklist
--------------------------

* ``--dev`` off, ``list_db = False``, ``admin_passwd`` changed.
* ``proxy_mode = True`` behind a reverse proxy, with ``http_interface`` bound to
  localhost.
* ``dbfilter`` set, and ``server_wide_modules`` minimal (default
  ``base,rpc,web``).
* ``workers > 0``, with ``limit_time_cpu``, ``limit_time_real``,
  ``limit_memory_soft`` and ``limit_request`` tuned; the hard memory cap is set
  by the service manager (cgroup ``MemoryMax=``), not by Odoo.
* ``db_sslmode = verify-full`` (``require`` at minimum). The default ``prefer``
  does not enforce TLS.
* ``gevent_port`` set for websockets, ``x_sendfile = True`` behind nginx or
  Apache, and ``data_dir`` on a persistent, backed-up volume.
* Python dependencies pinned with hashes, and ``pip-audit`` run regularly.

----

10.11 Authority context keys
----------------------------

**The context carries preferences, never authority** ``[review]``. An authority
key is a context key that does any of the following:

* skips a validation, a lock or an approval;
* widens what a user reaches;
* picks the company or the user;
* marks an install.

Examples are ``skip_readonly_check``, ``force_delete``, ``install_mode`` and
``uid``. Server code may set an authority key in-process. A client never may.
**Declare it with ``declare_authority_keys(owner, *keys)`` in
``odoo/tools/authority_keys.py`` (or at addon import), in the same change that
reads it.** Every client door strips declared keys, so a forged key never reaches
a model, while an in-process ``with_context`` still works. The doors are:

* ``call_kw`` and ``call_button``, ``/xmlrpc/2`` and MCP;
* the ``context`` parameter of JSON-RPC and json2 routes;
* the ``web_read`` and ``onchange`` field-spec contexts;
* the report and export routes.

Corollaries:

* **Never round-trip an authority key through the browser** ``[review]``. A
  wizard that returns an action carrying the key loses the key once it is
  declared. Carry the decision server-side, then declare the key. Keys still
  undeclared for this reason: ``skip_consumption`` (mrp) and ``skip_expired``
  (product_expiry).
* **A key compared by identity to an ``object()`` sentinel needs no
  declaration** (``bypass_audit``, ``skip_captcha_login``,
  ``bypass_restricted_rendering``). JSON cannot produce that object.
* **Raw SQL never takes a company, a user or a scope from the context**
  ``[review]``. Read ``self.env.company`` / ``self.env.companies``. A field that
  exposes the result carries the ``groups=`` of the model the SQL reads past.

11. Performance
===============

11.1 N+1 queries
----------------

**No ``search``, ``search_count``, ``search_fetch``, ``search_read``,
``name_search`` or ``_read_group`` inside a loop over records**
``[test_lint E8507]``. The rule has a hard zero. It is syntactic, so a loop that
runs one query per *distinct key* (company, model, timezone, grouped domain, a
single-record wizard) is waived with ``# noqa: E8507 - <the key>``. Hoist a loop
over the records themselves. Never waive it.

**Batch writes too: no ``create``, ``write`` or ``unlink`` per iteration where
the values can be built first** ``[review]``. E8507 does not see writes. Pin
them with ``assertQueryCount``.

.. code-block:: python

   groups = self.env["child.model"]._read_group(
       [("parent_id", "in", records.ids)], ["parent_id"], ["__count"],
   )
   count_map = {parent.id: count for parent, count in groups}
   for record in records:
       record.child_count = count_map.get(record.id, 0)

Replace nested loops with an index built once (``defaultdict(list)`` keyed on
the parent id).

11.2 Batching and aggregation
-----------------------------

**Use the left column** ``[review]``:

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

* A group-less ``_read_group`` returns ``[(value,)]``. Unpack it twice:
  ``[[total]] = Model._read_group(domain, aggregates=["amount:sum"])``.
* **Count an x2many with ``fields.Count``, never ``len()`` in a compute and never
  a hand-written ``_read_group``** ``[review]``. On a list page, ``len(record.line_ids)``
  fetches and instantiates every line. On a form, or on a new record, ``len()``
  is the cheapest option. ``fields.Count`` picks the right branch per call.
* For a large set processed one record at a time, use ``with_prefetch([])`` to
  stop sibling prefetch.

11.3 ``ormcache``
-----------------

Use ``@ormcache`` for read-heavy, rarely changing data: metadata, parsed views,
ACL lookups, config values.

.. code-block:: python

   from odoo.tools import ormcache

   @ormcache("self.env.uid", "model_name")
   def _get_access_rights(self, model_name):
       ...

**A cached method never returns a recordset** ``[review]``. Its cursor is closed
by the next call, which then raises ``InterfaceError``. Return plain values.
Invalidation happens through ``modified()``, and
``self.env.registry.clear_cache()`` clears everything.

11.4 Computed fields
--------------------

* **``store=True`` only when the field is searched, ordered or grouped on**
  ``[review]``.
* **``@api.depends`` names every sub-field path the body reads** ``[review]``.
  For example, reading ``rec.partner_id.country_id`` needs
  ``"partner_id.country_id"``. ``"partner_id"`` alone leaves the value stale.
* **Exception: an initialisation-only compute** (``store=True, readonly=False``)
  depends on the coarse ``"parent_id"`` on purpose. The precise path would
  overwrite the user's edit. A field whose ``inverse`` writes back along the same
  path coarsens it too, to avoid a trigger cycle.
* **Flatten chains of stored computes that depend on each other** ``[review]``.

11.5 Indexing
-------------

* **Set ``index=True`` on fields used in domains, ``ORDER BY`` or ``GROUP BY``**
  ``[review]``. Every index costs write time. Beyond the rule below, add one only
  when a query plan shows the need.
* **Index the stored inverse Many2one of every One2many**
  ``[test_lint test_index]``. Without the index, each traversal is a sequential
  scan. Record an exception with its reason in ``BTREE_INDEX_IGNORE_MODELS`` /
  ``BTREE_INDEX_IGNORE_FIELDS``, never as a bare ``index=False``.
* Declare composite, partial and expression indexes with ``models.Index()``:

  .. code-block:: python

     _account_date_idx = models.Index("(account_id, date)")
     _state_date_idx = models.Index("(date_order) WHERE state != 'done'")
     _name_upper_idx = models.Index("(UPPER(name))")

* Prefer a partial index where queries always filter on a state. Use an
  expression index for case-insensitive lookups. ``USING gin`` and
  ``USING brin`` (append-only time series) need a query plan as justification.

11.6 Raw SQL
------------

**Every new raw ``cr.execute()`` ships ``EXPLAIN ANALYZE`` output in the PR,
showing the expected index use** ``[review]``. For parameter placement, see
§10.4 (``IN``, ``ANY``, ``INTERVAL``).

**Bracket raw SQL with a flush and an invalidation** ``[review]``:

.. code-block:: python

   self.flush_model()
   self.env.cr.execute(...)
   self.invalidate_model()

**Never repeat a parameterised SQL expression in one statement unless it has
been ``.inlined(self.env.cr)``** ``[review]``. Each ``%s`` becomes its own
``$N``. The same expression in the SELECT list and in GROUP BY is therefore two
expressions to PostgreSQL, which raises ``GroupingError`` whatever the values.
The usual carrier is a translated field, because ``_field_to_sql`` binds the
language. Alternatively, group by the raw column or the select alias.

11.7 Cron batching
------------------

**A cron over a large set batches and reports progress through
``_commit_progress``, and never calls ``cr.commit()``** ``[review]``.

.. code-block:: python

   for orders in self.env["sale.order"].search_iter(
       [("state", "=", "pending")], batch_size=100
   ):
       orders._process()
       if not self.env["ir.cron"]._commit_progress(processed=len(orders)):
           break

* **Batch 100–1000 records** ``[review]``. This bounds memory and lock duration.
* **Walk a set with ``search_iter(domain, batch_size=)``** ``[review]``. It is
  mandatory when the domain shrinks as rows are processed. Each batch is a
  keyset search on ``id``, so it has no offset drift and holds no whole-set id
  list. When the total is needed, call ``_commit_progress(0, remaining=n)`` once
  before the loop.
* **Batch a plain iterable with ``itertools.batched``** ``[review]``.
  ``split_every`` no longer exists (Appendix C).
* ``_commit_progress(processed=0, *, remaining=None, deactivate=False)``:
  ``remaining`` is keyword-only. The call returns the remaining cron **time in
  seconds** (``inf`` outside a cron, ``0`` at the deadline). Set ``remaining``
  once, then pass only ``processed``. Pass ``deactivate=True`` on the final call
  of a one-shot cron.

11.8 Locking
------------

**Lock rows with the recordset verbs, never raw ``FOR UPDATE``, unless the
statement cannot be expressed by them** ``[review]``. The verbs dispatch through
``env.backend``, so the in-memory tier answers them too.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Verb
     - Statement and use
   * - ``lock_for_update()``
     - ``FOR UPDATE SKIP LOCKED``. Raises ``LockError`` unless every row was
       taken. Use it for critical sections that must not wait.
   * - ``lock_for_update(wait=True)``
     - ``FOR UPDATE`` ordered by ``id`` (deadlock-free). Blocks until the
       holder commits. Wrap it in a ``lock_timeout`` where waiting forever is
       wrong.
   * - ``try_lock_for_update(limit=)``
     - ``FOR UPDATE SKIP LOCKED``. Returns the rows it took. Use it for job
       queues and cron dispatch.
   * - ``allow_referencing=True``
     - ``FOR NO KEY UPDATE`` with any verb above. Does not block a concurrent
       ``INSERT`` that references the row.

**Lock to serialize a decision, not to relieve contention** ``[review]``.
REPEATABLE READ plus ``retrying()`` already handles two writes to one row. A
lock there only moves the failure and costs throughput
(``doc/architecture/qualities.md``, Scenario 5). Lock where there would otherwise
be **no** conflict: a decision read from a set of rows and written to a
different row (``TestORM.test_the_lock_is_what_makes_a_read_of_a_set_conflict``).

Raw ``FOR UPDATE`` is for what the verbs cannot express:

* a lock that also reads a column in the same round trip;
* ``UPDATE ... SET write_date = write_date`` to force a serialization failure on
  the peer.

Lock, operate and commit fast.

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

* **Name the directory after the manifest ``version`` without the series prefix**
  ``[test_lint lint_migration_series_prefix]``. Manifest ``19.0.1.2.0`` gives
  directory ``1.2.0``. Why: a bare directory compares only the version tail, so
  it is skipped correctly on a database from an older series, while a prefixed
  directory re-runs there.
* **A directory pinned to an older series (``15.0.5.0``) is legitimate.** It
  names an absolute version on a multi-series path. A name of neither shape is
  skipped silently ``[test_lint lint_migration_version_unreadable]``.
* ``0.0.0`` runs on **every** update: first in ``pre``, last in ``post`` and
  ``end``.
* Scripts match on the stage prefix alone (``pre-``, ``post-``, ``end-``), so
  ``post-migrate_update_taxes.py`` runs. Within a stage, scripts run in filename
  order.
* **``migrate`` takes exactly two positional parameters, ``(cr, version)``**.
  ``_cr`` and ``_version`` are the only accepted aliases. Any other signature
  raises ``TypeError`` mid-upgrade.
* **Migration scripts are held to the same lint as other code, except ``E501``
  and ``ERA``** ``[review]``. They target Python 3.14 like the rest of the tree,
  so ``UP`` and ``PTH`` apply. ``ruff.toml``'s ``**/migrations/**`` ignore list
  still holds ``UP`` and ``PTH``. Remove both.

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

**Guard SQL with ``odoo.db.schema`` helpers, never hand-written
``information_schema`` queries** ``[review]``. The helpers are
``table_exists``, ``column_exists``, ``index_exists``, ``create_column``,
``convert_column``, ``drop_columns`` and ``drop_constraint``. The framework
passes a cursor, not an environment. ``odoo.tools.sql`` does not exist.
``openupgradelib`` is not the house default.

**Harvest a removed stored field's values in ``post-migrate`` of the same
version** ``[review]``. ``ir.model.data._process_end`` drops the column
(``DROP COLUMN CASCADE``) after every ``post-migrate``. Nothing is left for a
later version.

**A field that stops being stored ships a ``post-migrate`` calling
``schema.drop_columns(cr, table, columns)``** ``[review]``. The ORM never drops a
column, and the field row survives, so ``_process_end`` deletes nothing. A
``related=`` that loses ``store=True`` (§2.3, ``E8529``) is the common case. Use
one call per table, because each ``ALTER TABLE`` takes an exclusive lock. The
call cascades: a dependent report view is dropped, logged, and rebuilt by its
``init()`` in the same upgrade.

**Drop a removed code-defined Many2many's relation table yourself, or state in
the script that it is kept** ``[review]``. ``_drop_m2m_tables`` only drops
``manual`` fields, so the join table, its rows and its foreign keys otherwise
stay forever.

**Copy and link in one ``post-migrate``, never split across versions**
``[review]``. ``migrate_module`` runs every ``pre`` script in range before any
``post`` script. A higher version's ``pre`` "drop" therefore runs before a lower
version's ``post`` "copy", and the data is lost without error.

12.3 When one is required
-------------------------

**Required**: adding or removing a required field on an existing model; changing
a field's type; renaming a model or field; any non-trivial data transformation.

**Not required**: adding an optional field; installing a new module; view-only
changes; adding or removing a Many2many relation.

12.4 What a migration cannot reach
----------------------------------

**Never fix rows a model discovers from the registry in a migration**
``[review]``. ``run_end_migrations()`` runs before ``register_model_hooks()``
(``odoo/modules/loading.py``). A migration therefore matches nothing and reports
success. This is the same failure as §2.4.14.

**Derive such rows in ``_register_hook``** ``[review]``. It runs on every
registry load, after every module is in, and it also carries values over from
legacy parameters.

**Guard a hook that queries its own model with
``table_exists(self.env.cr, self._table)``** ``[review]``. Without the guard, a
database whose module predates the table cannot boot, not even to upgrade.

----

Appendix A — Fork field renames
================================

**Use the fork name; the vanilla name raises** (``ValueError`` on write or
search, ``AttributeError`` on read, a 500 over JSON-RPC and MCP). Apply these
regardless of what training data suggests. ``[review]``

``project.task``:

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
     - ``personal_triage_id`` (Many2one → ``project.task.triage``). The
       separate related ``triage_id`` points at ``project.triage``.
   * - ``depend_on_ids``
     - ``predecessor_ids``
   * - ``dependent_ids``
     - ``successor_ids``
   * - ``planned_date_begin``
     - ``date_start`` (the planned window is ``date_start`` / ``date_end``)
   * - ``planned_date_start``
     - ``date_start_effective`` -- computed, unstored, NOT the start date: it
       falls back to ``date_end`` when ``date_start`` is unset
   * - ``earliest_start`` / ``latest_start`` (fork-only)
     - ``cpm_date_earliest_start`` / ``cpm_date_latest_start``

Do: ``("step_id.fold", "=", False)``, ``order="date_end asc"``.
Don't: ``("stage_id.fold", "=", False)``, ``order="date_deadline asc"``.

The rest of the project family (§2.3 prefixes):

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

**``date_deadline`` is wrong on ``project.task`` and right on
``project.milestone``.** The ``project.task`` search filter
``<filter name="deadline">`` groups by ``date_end`` and keeps its name.

Fork-only fields, listed so the list is one: ``project.baseline.line``
``date_planned_start`` / ``date_planned_end``; ``project.benefit``
``date_review`` / ``date_review_reminder``; ``project.gate`` ``date_review``;
``project.gate.criterion`` ``is_met``; ``project.retrospective.action``
``date_due``; ``project.project`` ``date_premortem`` /
``premortem_participant_ids``.

``purchase.order`` and ``purchase.order.line``:

.. list-table::
   :header-rows: 1

   * - Vanilla Odoo
     - This fork
   * - ``date_planned``
     - ``date_commitment`` (the name ``sale.order`` already uses;
       ``mixin.order``'s ``is_late`` reads it on both)

**``date_planned`` still exists with another meaning**: a derived, unstored
estimate on ``sale.order`` (and ``sale.order.line`` under ``sale_stock``), the
scheduling date on ``stock.move`` / ``stock.picking``, a procurement
``values`` key, and a replenishment-wizard field. Do not rename those.

``sale.order`` and ``pos.order``: ``stock_reference_ids`` → ``reference_ids``,
the name ``stock.move``, ``stock.picking``, ``purchase.order``,
``mrp.production`` and ``repair.repair`` use. The relation tables
``stock_reference_sale_rel`` and ``stock_reference_pos_order_rel`` keep their
names.

``res.partner``: the phone scalars became a related model
----------------------------------------------------------

``res.partner`` has **no** ``phone`` and **no** ``mobile``. Numbers are
``phone.number`` records (number, ``type`` mobile / landline / fax / whatsapp /
emergency, country, label, primary flag).

.. list-table::
   :header-rows: 1

   * - Vanilla Odoo
     - This fork
   * - ``phone``
     - ``phone_ids`` (Many2many → ``phone.number``); ``main_phone_id`` is the
       computed first active Landline, ``main_mobile_id`` the first active Mobile
   * - ``mobile``
     - the same ``phone_ids``, with ``type`` set to ``mobile``

.. code-block:: python

   # Don't: raises ValueError: Invalid field 'phone' in 'res.partner'
   partner.write({"phone": "555-0100"})
   # Do
   partner.write({"phone_ids": [Command.create({"number": "555-0100", "type": "mobile"})]})
   number = partner.main_mobile_id.number

**A fixture writing ``phone`` / ``mobile`` on a partner is a bug.** ``[review]``

``res.partner``: the two manufacturer flags
--------------------------------------------

Code written against ``product_manufacturer`` (or its OCA original) uses the
old names; the fields now live in ``product``.

.. list-table::
   :header-rows: 1

   * - ``product_manufacturer``
     - This fork
   * - ``manufacturer``
     - ``is_manufacturer`` (Boolean, label ``Manufacturer``)
   * - ``product_count``
     - ``count_manufactured_products`` -- a ``fields.Count`` over
       ``manufactured_product_ids``; unstored, no column

A view domain ``[('manufacturer', '=', True)]`` on ``res.partner`` raises when
the action or dropdown opens, not when the view loads. ``iot.device.manufacturer``
and ``device.profile.manufacturer`` are unrelated Char fields.

**A new counter takes the ``count_`` prefix (§2.3); the existing ``*_count``
family is exempt and is not mass-renamed** ``[review]``.

Order lines: ``product_qty`` and ``product_uom_qty`` swapped meanings
---------------------------------------------------------------------

On ``sale.order.line`` and ``purchase.order.line`` each name carries the
*other's* upstream meaning. ``mixin.order.line.amount``
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

**Write ``product_qty``; never write ``product_uom_qty``.**
``mixin.order.line.amount._check_write_derived_quantity`` raises on it from
``create`` and ``write``, including a command list assigned to the one2many
and a vals dict built in a variable. ``[review]`` + runtime check

**Read ``product_uom_qty`` only where the reference unit is the point** (a line
against free stock); read ``product_qty`` wherever the quantity is converted
from ``product_uom_id`` or compared with a BoM's ``product_qty``. ``[review]``
``stock.move.product_uom_qty`` is unrelated: a real, writable field.

``hr.expense``:

.. list-table::
   :header-rows: 1

   * - Model
     - Vanilla Odoo
     - This fork
   * - ``hr.expense``
     - ``approval_state``
     - ``review_state`` ("Review Status": submitted / approved / refused).
       ``approval_state`` is the ``mixin.approval`` request's state. The 2.3
       migration rewrote saved views, filters, actions and export lines.

``maintenance`` (``date_`` first, named for what it dates; the 1.7 migration
renames columns and rewrites stored expressions):

- ``maintenance.order.date_confirmed`` is stamped when the order leaves draft
  and cleared when it returns there; reliability counts its local day as the
  failure.
- ``maintenance.order.owner_user_id`` is gone: the requester is ``create_uid``.

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
   * - ``maintenance.order``
     - ``owner_user_id``
     - ``create_uid``
   * - ``maintenance.plan``
     - ``date_start`` / ``date_next``
     - ``date_first_occurrence`` / ``date_next_scheduled``
   * - ``maintenance.profile`` (read through ``mixin.maintenance.target`` on
       ``resource.asset``, ``mrp.workcenter``)
     - ``date_effective`` (vanilla ``effective_date``)
     - ``date_in_service``
   * - ``maintenance.profile`` (same hosts)
     - ``latest_failure_date`` / ``estimated_next_failure``
     - ``date_last_failure`` / ``date_next_failure``
   * - ``team.team``
     - ``maintenance_todo_order_count_date``
     - ``maintenance_todo_order_count_scheduled``

Appendix B — References
========================

In this repo (paths relative to the ``odoo/`` checkout):

* ``ruff.toml`` -- linter and formatter configuration, with the rationale for
  every suppression
* ``odoo/addons/test_lint/`` -- the fork's own checkers
* ``odoo/addons/test_lint/tests/floors.json`` -- the committed ``test_lint`` floors
* ``pytest.ini`` -- the Tier 1 and Tier 2 suite definitions
* ``.github/workflows/gates.yml`` -- CI: ``./gates.sh`` and ``--perf-counts``
* ``doc/architecture/gates.md`` -- what is enforced and how to run it

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

**Never write a retired pattern. Every existing occurrence is debt: replace it
when found, and do not leave it for an unrelated edit.** ``[review]``

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Retired
     - Replacement
   * - Suffix XML IDs (``sale_order_view_form``)
     - Prefix style (§3.2)
   * - Commit tags ``[MIG]``, ``[CLA]``
     - ``ADD`` / ``REF`` on the migration script; ``REF`` on the licence change
       (§7.1)
   * - Suffix mixin names (``x.mixin``); an abstract mixin with no marker
     - Prefix ``mixin.`` (§2.2.1)
   * - Two model classes in one ``models/*.py``
     - One per file, named from ``_name`` (§1.3)
   * - Field ordering by type
     - Semantic blocks (§2.3)
   * - Method ordering by Spanish category
     - The member order in §2.2
   * - Google-style docstrings (``Args:``, ``Returns:``)
     - Sphinx fields (§2.5)
   * - ``<tree>`` views and ``view_mode`` ``tree``
     - ``<list>`` (§3.3)
   * - ``attrs=`` / ``states=``
     - Python expressions ``invisible=`` / ``readonly=`` / ``required=`` (§3.3)
   * - Renaming an inherited core method to fit §2.4
     - Override under the original name (§2.4)
   * - ``split_every``
     - ``itertools.batched`` (§11.7)
   * - ``with_context(force_company=...)``
     - ``with_company()`` (§2.6). Why: the key is ignored with only a
       ``DeprecationWarning``, so the call silently uses the wrong company.
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
     - The row the body belongs to (§2.4.20): ``_normalize_`` reshapes a value,
       ``_filter_`` a subset, ``_update_`` an in-place mutation, ``_prepare_`` a
       payload, ``_check_`` raises. Reserved for HTML sanitisation and for a hook
       named after a ``sanitized_*`` field
   * - Writing ``phone`` / ``mobile`` / ``manufacturer`` / ``product_uom_qty``
       (order line) or any vanilla name in Appendix A
     - The fork name (Appendix A)

Appendix D — Document history
==============================

One row per change, one clause. Versions 6.10–6.16 each name two changes (an
``addons/`` block between 6.26 and 6.25, a core block below 6.17); disambiguate
them by the scope in each row's first clause, not by date or position.
``tests/framework/test_guidelines_header.py`` pins exactly these seven
collisions, so an eighth fails and so does a renumbering.

.. list-table::
   :header-rows: 1
   :widths: 8 12 80

   * - Version
     - Date
     - Summary
   * - 7.0
     - 2026-09-22
     - Rewrite: narration, measurement histories and deleted-tooling
       internals removed (9764 -> 6216 lines); every ``[ratchet]``/``[gate]``
       label without a live ``test_lint`` floor reads ``[review]``; false
       claims corrected against the tree. Rules strengthened: ruff check and
       format clean in every repo, C901 <= 20, ESLint zero, BLE001, bare
       ``_()`` banned for ``self.env._``, group-less ACL lines banned, no raw
       ``cr.commit()`` in crons, psycopg 3 ``IN``/``= ANY`` (E8534), secrets in
       ``credential.credential``; §7 describes the commit shape in use;
       §2.5 matches the no-docstring policy.
   * - 6.67
     - 2026-09-22
     - §4.3.1: OWL templates name component members ``this.x`` and call with
       parametric ``t-call``; the codemod's ``--check`` is the gate.
   * - 6.66
     - 2026-09-22
     - §4.3.1: OWL templates write ``t-out``; ``t-esc`` is a hard zero
       (``test_owl_templates.py``) ahead of the OWL 3 switch.
   * - 6.65
     - 2026-09-22
     - §10.11: the context carries preferences, never authority; authority
       keys are declared in ``odoo/tools/authority_keys.py`` and stripped at
       every door. §10.8's read-only tier points at each app's
       ``test_group_readonly.py`` instead of the deleted ``readonly_tiers``.
   * - 6.64
     - 2026-09-22
     - §11.8 states what a lock is for, measured: REPEATABLE READ already
       detects a same-row write conflict, so locking first only moves the
       failure earlier at 10-22 % throughput; the lock is for a decision read
       from a set, where there would otherwise be no conflict at all.
   * - 6.63
     - 2026-09-22
     - §11.7 names ``search_iter`` (new: a keyset walk, one search per batch
       on the last id seen) for a domain that shrinks as it is processed.
   * - 6.62
     - 2026-09-22
     - §11.8 names the recordset lock verbs -- ``lock_for_update()``, its
       ``wait=True`` form (new: ``FOR UPDATE`` ordered by id, queueing
       behind the holder) and ``try_lock_for_update(limit=)`` -- and leaves
       raw ``FOR UPDATE`` to the two shapes they cannot express.
   * - 6.61
     - 2026-09-21
     - Appendix D states its own 6.10-6.16 collision: two §2.4 campaigns
       numbered from the same point, disambiguated by scope because five rows
       of each share a date. Renumbering priced at 32 cascading rows and five
       unamendable commit-body citations left pointing at different changes,
       and rejected on that.
   * - 6.60
     - 2026-09-21
     - §1.4/commit-citation: a machine doc's citation of a live method is
       rewritten, not frozen. Freezing protects a figure whose argument rests
       on a base commit; a name carries no argument, and a dead one misleads
       the reader the doc exists for.
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
       the gates run as one command (``./gates.sh``).
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
