import sys
from pathlib import Path

from odoo.libs.debug_log import DebugLog
from odoo.orm.stubs import STUB_MODULE, render_registry

from . import DatabaseCommand, open_environment

_debug = DebugLog(__name__)


class Stubs(DatabaseCommand):
    description = (
        "Write typed stubs of a database's registry, one class per model, "
        "for mypy through mypy_registry_plugin"
    )

    def __init__(self) -> None:
        super().__init__()
        self.add_config_arguments(self.parser)
        self.parser.add_argument(
            "-o",
            "--output",
            dest="output",
            help=f"directory that receives {STUB_MODULE}.pyi (default: the data dir)",
        )

    def run(self, cmdargs: list[str]) -> None:
        parsed_args, unknown = self.parse_args(cmdargs)
        db_name = self.bootstrap_config(parsed_args, extra_args=unknown)
        with open_environment(db_name, readonly=True) as env:
            source = render_registry(env.registry)
            models = len(env.registry.models)
        if parsed_args.output:
            directory = Path(parsed_args.output)
        else:
            from odoo.tools import config

            directory = Path(config["data_dir"]) / "stubs" / db_name
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{STUB_MODULE}.pyi"
        target.write_text(source)
        _debug.lifecycle(
            "cli.stubs.written", db=db_name, models=models, path=str(target)
        )
        print(f"{target}: {models} models", file=sys.stderr)
