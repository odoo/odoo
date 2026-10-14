import copy
import json
import subprocess
import tempfile
from pathlib import Path
from unittest import skipIf

from odoo.modules import Manifest
from odoo.tools.misc import find_in_path

from .common import LintCase

try:
    tsc = find_in_path("tsc")
except OSError:
    tsc = None

MODULES_TO_CHECK = {
    "web",
}

BASE_TS_CONFIG = {
    "compilerOptions": {
        "allowUmdGlobalAccess": True,
        "module": "preserve",
        "target": "es2022",
        "allowJs": True,
        "noEmit": True,
        "paths": {},
        "typeRoots": [],
    },
    "include": [],
    "exclude": [
        "node_modules",
        "**/lib/ace",
        "**/lib/bootstrap",
        "**/lib/Chart",
        "**/lib/chartjs-adapter-luxon",
        "**/lib/fullcalendar",
        "**/lib/luxon",
        "**/lib/owl",
        "**/lib/pdfjs",
        "**/lib/popper",
        "**/lib/signature_pad",
        "**/lib/stacktracejs",
        "**/lib/zxing-library",
        "**/src/o_spreadsheet/o_spreadsheet.js",
    ],
}


@skipIf(tsc is None, "tsc not found on this system")
class TestTypeScript(LintCase):
    def _get_manifest(self, module_name: str):
        manifest = Manifest.for_addon(module_name)
        if not manifest:
            raise RuntimeError(f"Module '{module_name}' not found")
        return manifest

    def _get_all_dependency_manifests(self, modules: set[str]) -> dict[str, Manifest]:
        dependency_manifests = {
            module: self._get_manifest(module) for module in modules
        }

        def _get_missing_manifests():
            missing = []
            for manifest in dependency_manifests.values():
                missing += [
                    dep for dep in manifest["depends"] if dep not in dependency_manifests
                ]
            return missing

        while missing := _get_missing_manifests():
            dependency_manifests |= {
                module: self._get_manifest(module) for module in missing
            }

        return dependency_manifests

    def _build_ts_config_for_modules(self, modules: set[str]):
        manifests = self._get_all_dependency_manifests(modules)
        ts_config = copy.deepcopy(BASE_TS_CONFIG)
        for module_name, manifest in manifests.items():
            static_src_path = f"{manifest.path}/static/src"
            if not Path(static_src_path).exists():
                continue
            ts_config["compilerOptions"]["paths"][f"@{module_name}/*"] = [f"{static_src_path}/*"]
            ts_config["compilerOptions"]["typeRoots"] += [f"{static_src_path}/@types"]
            ts_config["include"] += [f"{static_src_path}/**/*.js", f"{static_src_path}/**/*.ts"]

        return ts_config

    def _run_typescript_for_ts_config(self, ts_config: dict):
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as f:
            f.write(json.dumps(ts_config))
            f.flush()
            cmd = [tsc, "-p", f.name]
            return subprocess.run(cmd, capture_output=True, encoding="utf-8", check=False)

    def test_typescript(self):
        ts_config = self._build_ts_config_for_modules(MODULES_TO_CHECK)
        tsc_result = self._run_typescript_for_ts_config(ts_config)
        if tsc_result.returncode != 0:
            self.fail(tsc_result.stdout)
