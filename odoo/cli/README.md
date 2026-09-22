# `odoo.cli` — command entry points

`odoo-bin` is three lines: `import odoo.cli; odoo.cli.main()`. Everything a shell can ask
of the server goes through this package; nothing in the serving tier (`orm/`, `service/`,
`http/`, `modules/`) imports it back (`doc/architecture/module.md`, rule
`orm-below-the-serving-tier`). Two module globals are read from outside: `odoo.cli.COMMAND`
(the command name, consulted by `odoo/tests/common.py` and `odoo/tests/shell.py`) and
`odoo.cli.BOOTSTRAP_ADDONS_PATH` (the `--addons-path` that preceded the command name,
merged by `start`).

## Module map

| Module | Command | Base | Parses the config (sets up logging) |
|---|---|---|---|
| `command.py` | — | `Command`, `DatabaseCommand`, `main()`, discovery, `open_environment` | — |
| `server.py` | `server` (the default) | `Command` | `run_server` → `config.parse_config(setup_logging=True)` |
| `start.py` | `start` | `Command` | pre-parses its own args, then `run_server` |
| `shell.py` | `shell` | `Command` | `_start_server` |
| `db.py` | `db init\|load\|dump\|duplicate\|rename\|drop\|list` | `Command` | `run`, from the connection flags |
| `module.py` | `module install\|upgrade\|uninstall\|force-demo` | `DatabaseCommand` | `bootstrap_config` |
| `i18n.py` | `i18n import\|export\|loadlang` | `DatabaseCommand` | `bootstrap_config` |
| `populate.py` | `populate` | `DatabaseCommand` | `bootstrap_config` |
| `neutralize.py` | `neutralize` | `DatabaseCommand` | `bootstrap_config` |
| `obfuscate.py` | `obfuscate` | `DatabaseCommand` | `bootstrap_config` |
| `cloc.py` | `cloc` | `DatabaseCommand` | `bootstrap_config` only when `-d` is given or `-p` is not |
| `stubs.py` | `stubs` | `DatabaseCommand` | `bootstrap_config`; writes `odoo_registry_stubs.pyi` (one class per model of the database's registry, every field typed, relational fields typed to their comodel's class, the models' own methods) for mypy through the repo-root `mypy_registry_plugin.py`, which types `env["<name>"]` from it |
| `deploy.py` | `deploy` | `Command` | **never** — an HTTP client, no config, no logging setup |
| `scaffold.py` | `scaffold` | `Command` | **never** |
| `help.py` | `help` | `Command` | **never** |

The last column matters twice. A `--log-handler` (or any server option) reaches a command
only through the args it forwards to `config.parse_config`, so it goes **after** the
subcommand (`odoo-bin db list --log-handler …`, not before), and the three commands that
never parse a config reject it and print nothing at DEBUG from a shell — their loggers
reach a handler only in-process (`/base:TestCommand`, or a script that installs one).

## The spine

`main()` strips a leading `evented` (sets `odoo.evented`), pre-parses `--addons-path`, picks
the command name (first positional, or `help` for `-h`/`--help`, else `server`), resolves it
with `get_cli_command`, and calls `Command().run(args)`.

- **Registration is by subclassing.** `Command.__init_subclass__` registers the class under
  `cls.name or cls.__name__.lower()`, and refuses a name that is not `[a-z][a-z0-9_]*`,
  that differs from the defining module's stem, or a class that does not override `run`. A
  base class opts out with `class X(Command, register=False)` — that is how
  `DatabaseCommand` exists without being a command. A second registration of the same name
  wins, with a warning.
- **Resolution is lazy.** `get_cli_command(name)` imports `odoo.cli.<name>` if the name is
  not registered yet, then scans every addons path for `<addon>/cli/<name>.py` and loads
  it as `odoo.cli.<name>` (`load_addons_commands`); a later addon shadows an earlier one,
  with a warning. `help` is the only command that loads everything
  (`load_internal_commands` + `load_addons_commands()` with no name).
- **`DatabaseCommand`** adds `-c/--config`, `-d/--database`, `-D/--data-dir` to a parser
  (`add_config_arguments`, `default=SUPPRESS` on a subparser so the top-level value
  survives), and `bootstrap_config` turns the parsed namespace plus the unknown args into
  one `config.parse_config(..., setup_logging=True)` call, then resolves the single database
  through `get_single_database` — exactly one, and never a maintenance database
  (`postgres`, `template*`, the configured `db_template`).
- **`open_environment(db_name, readonly=, context=, uid=, new_registry=)`** is the one way
  a command gets an `Environment`: `Registry(db)` (or `Registry.new`), one cursor, the
  superuser unless told otherwise. `module` asks for `new_registry=True` because
  `button_immediate_*` reload the registry underneath it.

## Load-bearing facts

- `db` refuses `dump` of a system database, and every subcommand routes its target through
  `check_db_not_maintenance`; `load` accepts only a zip (`pg_restore`/`psql` for the rest)
  and a URL is spooled to a 256 MB `SpooledTemporaryFile` before restore.
- `module install` filters the requested names by presence on disk, then splits the
  already-installed ones out (`_split_installed`, logged as "Already installed, nothing to
  do") so `button_immediate_install` — a registry reload, ~0.8 s on a base-only database —
  runs only when something is left to install. Every `module` subcommand but `force-demo`
  pays `ir.module.module.update_list()` first (~0.6–0.8 s, 121 statements on base alone).
- `obfuscate` keeps a password marker in `ir_config_parameter` (`odoo_cyph_pwd`) and a
  `pg_temp` function per connection; `--allfields` is unobfuscate-only and reads
  `information_schema.columns` restricted to `BASE TABLE`s (a view broke it before
  `6bbac7ead1e3`); `ir_*` tables are never touched.
- `deploy` treats a bare host as `http://` only for `localhost`/`127.0.0.1`/`0.0.0.0`/`::1`,
  else `https://`. The server side (`base_import_module`'s `login_upload`, a read/write
  route) answers a refused login or a non-admin with 403, another `UserError` with 400,
  anything else with 500, the message as body; `deploy` prints that body
  (`refused the upload: 403 FORBIDDEN — Access Denied`). A success is a 200 with an empty
  body.
- `shell` tries `ipython`, `ptpython`, `bpython`, `python` in that order (or the
  `--shell-interface` first, `python` as fallback), rolls the cursor back before and after
  the session, and runs piped stdin as a script instead of a REPL.
- `start -p` is `--path`, not the server's `--http-port`; it derives `--addons-path`,
  `-d` and `--db-filter` from the project directory unless each is given.

## Tracing (campaign instrumentation, temporary)

Every module carries `_debug = DebugLog(__name__)` (`odoo/libs/debug_log.py`) and logs on
four channels named `odoo.debug.<channel>.cli.<module>` — `logic` (which branch, on what
input, every refusal with a `reason=`), `perf` (spans with `ms=` and, when a cursor is
given, `queries=`), `pipeline` (hand-offs: config bootstrapped, candidates resolved, zip →
upload), `lifecycle` (command entered / done, database created / loaded / dropped, module
installed / upgraded, pid file written / removed). Off by default; nothing prints at
`log_level = info`. Enable the whole package with four handlers
`--log-handler odoo.debug.<channel>.cli:DEBUG`, one channel with `odoo.debug.perf.cli:DEBUG`,
one command with `odoo.debug.logic.cli.obfuscate:DEBUG` — after the subcommand, see above.

The spine every `DatabaseCommand` run shares: `cli.config.bootstrapped` →
`cli.database.selected` → `cli.<command> subcommand=` → `cli.open_environment` →
`cli.registry ms=` → *the command's own work* → `cli.environment ms= queries=` →
`cli.environment.closing models=` → `cli.<command>.done` → `cli.command.done`. What sits
between `cli.registry` and `cli.environment` is the command; the `queries=` on
`cli.environment` counts the command's own cursor, not the cursors `button_immediate_*`
open for themselves. Lines that fire before `parse_config` — `cli.command`,
`cli.command.resolved`, `cli.commands.*`, `cli.args.parsed`, `cli.cloc.mode`, `cli.start.*`
— reach a handler only in-process. Correlate on `db=`, `subcommand=`, `table=`
(obfuscate), `lang=` (i18n), `module=` (module, scaffold, deploy). A log-only variable is
marked `x = ...  # debuglog`. The sites are removed together when the campaign ends; the
recipe, the cost figures and the first findings are in
`agromarin-knowledge/reference/dev/debug-logging-campaign.md` under "Core packages / cli".

## Tests

- `odoo/addons/base/tests/test_cli.py` (`/base:TestCommand`, 82 tests): registration rules,
  `help` covering every module here, discovery surviving a broken addon `cli/` file, `db`
  and `start` argument handling, `deploy` URL and exclusion rules, `obfuscate` field
  selection, `populate` factors, and the source-level pins (`re.escape` in `start`'s
  db-filter, `starts_with(table_name, 'ir_')` and `BASE TABLE` in `obfuscate`).
- `tests/process/` boots real `odoo-bin` processes through this package (`conftest.py`,
  `test_exit_code.py`, the reload-continuity suite).
