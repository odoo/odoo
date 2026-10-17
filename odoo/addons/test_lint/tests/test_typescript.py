import copy
import json
import subprocess
import tempfile
from unittest import skipIf

from odoo.modules import Manifest
from odoo.tests import BaseCase, tagged
from odoo.tools.misc import find_in_path

try:
    tsc = find_in_path("tsc")
except OSError:
    tsc = None

MODULES_TO_CHECK = [
    "web",
]

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
@tagged("at_install", "-post_install")
class TestTypeScript(BaseCase):
    def _upstream_dependencies(self, manifest: Manifest) -> set[str]:
        dependency_manifests = [Manifest.for_addon(dependency) for dependency in manifest["depends"]]
        dependencies = set(manifest["depends"] + [manifest.name])
        for dep_manifest in dependency_manifests:
            assert dep_manifest is not None
            dependencies |= self._upstream_dependencies(dep_manifest)
        return dependencies

    def _build_ts_config_for_module(self, module_name: str):
        manifest = Manifest.for_addon(module_name)
        if not manifest:
            raise RuntimeError(f"Module '{module_name}' not found")
        dependencies = self._upstream_dependencies(manifest)

        ts_config = copy.deepcopy(BASE_TS_CONFIG)
        for dependency in dependencies:
            manifest = Manifest.for_addon(dependency)
            assert manifest is not None
            static_src_path = f"{manifest.addons_path}/{dependency}/static/src"
            ts_config["compilerOptions"]["paths"][f"@{dependency}/*"] = [f"{static_src_path}/*"]
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
        for module in MODULES_TO_CHECK:
            with self.subTest(module=module):
                ts_config = self._build_ts_config_for_module(module)
                tsc_result = self._run_typescript_for_ts_config(ts_config)
                if tsc_result.returncode != 0:
                    self.fail(tsc_result.stdout)
