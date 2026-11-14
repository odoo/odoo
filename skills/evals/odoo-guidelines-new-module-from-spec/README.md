# odoo-guidelines-new-module-from-spec

Build a feature from a business spec, as a developer does from a product
team's request. The evals of the review and security skills measure what an
agent finds in code it reads; this one measures the code it writes: whether
it runs, whether it does what the spec asks, and how it follows the house
rules (odoo-guidelines, odoo-web-guidelines, odoo-security).

The feature is network printing: print shipping labels and any report
straight to Epson ePOS and Zebra ZPL printers from the browser, and print
carrier labels automatically when a delivery is validated. Odoo added it in
odoo/odoo 416f6c07faa4 (April 2026): a new `printer` module, and what
`stock_delivery` built on it.

- Checkout: master at c8d7430e (20.1 alpha), on branch
  `master-network-printing-jdoe`, without the feature, folded into the single
  commit: `addons/printer` is deleted, and `environment/remove.patch` takes
  out what stock_delivery built on it (the Shipping Labels and Shipping
  Documents reports, the automatic printing options of operation types, the
  printer menus, access row, demo data and tour), stock_delivery's
  translation entries for them, and the module's entries in `.weblate.json`
  and the JS tooling config. stock_delivery installs with demo data and its
  37 remaining tests pass. The remote is removed.
- Spec: `/home/odoo/spec.md` (`environment/spec.md`), in business terms, plus
  the printers' interfaces (the ZPL and ePOS-Print requests) as a developer
  would take them from the manufacturers' documentation. No module, model,
  field or method name. Where the original behaves less naturally than a spec
  would say (shipping reports printed as a download need a printer set on the
  report), the spec follows the original, so that the oracle scores full
  marks.
- Instruction: implement the spec, with tests, and commit it. The design is
  the agent's: a new module or not, extending stock_delivery or bridging it.
- Graded on:
  - `runtime` (deterministic, `tests/runtime`): the modules the agent added
    (a new `__manifest__.py`) or changed (translations aside) install without
    and with demo data and upgrade (exit codes); no error is logged while
    doing so (counted once); the views, window actions and menus they declare
    load; their static XML parses, the backend assets build, their new or
    changed JS passes `node --check`; the agent's own tests pass (those of
    new modules and of test files it added); no existing test of a module it
    changed breaks: an existing test that fails is re-run on the base commit,
    installed the same way, and counts only if it passes there (so tests
    that already fail with these modules installed, as some of stock's do
    with stock_delivery, are not held against the agent, and editing an
    existing test cannot hide a regression). Browser tours are skipped, the
    image has no Chrome. None of these needs a name from the spec.
  - `coverage` (LLM judges, `tests/coverage`): one binary criterion per
    behaviour of the spec (24, over three judges: printers, printing,
    shipping), judged on the new modules' sources and the diff of the
    changes to existing modules, with the original code as a reference
    (`tests/coverage/reference.txt`), never as the only correct design.
  - `guidelines` (LLM judge, `tests/guidelines`): one 5-point criterion per
    area of the rules (13, `architecture` included: which module each part
    goes in), against `tests/guidelines/rules.md`, a copy of the skills'
    rules made by `answer_key/sync_guidelines.sh` (rerun it after a change to
    the skills). The judge reads the spec too: a departure from a rule that
    the spec forces is not counted when a comment at that spot says so, as
    the guideline "Comment a deviation the requirements force" asks.
  - `design` (LLM judge, `tests/design`): the engineering choices compared
    with the original, one 5-point criterion per aspect (module design,
    extensibility, efficiency, robustness, tests, simplicity), 3 being on par:
    the original scores 0.5. Reported, weight 0 until a few runs show it is
    stable. Calibration outside Harbor: the original 3 on every aspect;
    Opus's run 0.875 (renders only what will be printed, simpler dialog,
    broader tests); Haiku's 0.58 and Sonnet's 0.63, both 2 on module design
    for building the capability on stock.
  - `reward`: runtime 3, coverage 4, guidelines 3, design 0.
- No module touched (the agent gave up) scores 0 on every dimension, judges
  skipped.
- The oracle (`solution/solve.sh`) puts back master's printer module
  (translations aside) and applies `solution/stock_delivery.patch`.

Most of the feature runs in the browser (the selection dialog, the choices
remembered per browser, the requests to the printers): it is judged from the
code only, as the image has no browser on arm64 hosts.

## Why not data_recycle

The first version of this task rebuilt `data_recycle` (old records cleanup).
In a run with the skills, Opus named its module `data_recycle` and reproduced
the original's models, fields and methods: its second command searched the
tree for a "recycle" module. Asked directly, Opus named the module and Sonnet
listed its fields. A feature the models recall measures their memory, not the
skills. Before choosing `printer`, the three Claude tiers were asked to name a
module matching its description: none knew it.
