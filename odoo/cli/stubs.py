import stat
import sys
import tempfile
from pathlib import Path

from odoo.libs.debug_log import DebugLog
from odoo.orm.stubs import STUB_MODULE, render_registry

from . import DatabaseCommand, open_environment

_debug = DebugLog(__name__)


def _write_stubs(target: Path, source: str) -> None:
    try:
        mode = stat.S_IMODE(target.stat().st_mode)
    except FileNotFoundError:
        mode = None
    with tempfile.TemporaryDirectory(
        dir=target.parent, prefix=f".{target.name}."
    ) as directory:
        temporary_path = Path(directory) / target.name
        temporary_path.write_text(source, encoding="utf-8")
        if mode is not None:
            temporary_path.chmod(mode)
        temporary_path.replace(target)


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
        _write_stubs(target, source)
        _debug.lifecycle(
            "cli.stubs.written", db=db_name, models=models, path=str(target)
        )
        print(f"{target}: {models} models", file=sys.stderr)
