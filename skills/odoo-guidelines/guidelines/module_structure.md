# Module structure and file naming

- Standard directories: `models/`, `views/`, `controllers/`, `data/`,
  `security/`, `static/`, and optional `wizard/`, `report/`, `tests/`,
  `populate/`.
- One model class per file, named after the model with dots as underscores
  (`res_partner.py`), whether the class defines a new model or extends an
  existing one with `_inherit`.
- Suffix conventions: backend views `*_views.xml`, portal/QWeb pages
  `*_templates.xml`, menus optional `*_menus.xml`, data `*_data.xml`, demo
  `*_demo.xml`, wizards `<transient>.py` + `<transient>_views.xml`.
- Security files: access rows in `security/ir.access.csv`; groups and other
  security records in `security/<module>_security.xml`.
- Controllers: feature-named files, or `<inherited_module>.py` when extending
  another module's controller (e.g. `portal.py`); `main.py` is legacy (still
  widespread in core).
- Reports: a statistics (SQL-view) report is `<model>_report.py` +
  `<model>_report_views.xml`; a printable report splits `<model>_reports.xml`
  (report actions, paperformat) from `<model>_templates.xml` (QWeb templates).
- `populate/` holds `populate.blueprint` XML records (`populate_demo.xml`,
  `benchmarks.xml`); an `__init__.py` makes it an importable package for
  custom populate generators.
- File and directory names are Python identifiers: lowercase, `[a-z0-9_]`.
