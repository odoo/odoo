import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from odoo.tests.common import BaseCase
from odoo.tools.assets import esbuild_stubs
from odoo.tools.assets.esbuild import _get_esbuild_path

from odoo.addons.base.models.assetsbundle import AssetsBundle


class TestEsbuildCompilerAddonFlagsSeam(BaseCase):
    def test_provider_is_threaded_into_compiler(self):
        def sentinel(root):
            return (["--alias:x=y"], [])

        fake = SimpleNamespace(
            name="some.bundle",
            native_modules=[],
            javascripts=[],
            _get_esbuild_addon_flags=sentinel,
        )
        compiler = AssetsBundle._prepare_esbuild_compiler(fake)
        self.assertIs(compiler._addon_flags_provider, sentinel)


def _build_probe_stub_mirror(tmp, files, stubs):
    odoo_root = Path(tmp)
    src_root = odoo_root / "addons" / "probe" / "static" / "src"
    for relpath, content in files.items():
        path = src_root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    stub_root = odoo_root / "stubs"
    layout = esbuild_stubs.stub_layout(
        stubs, ["--alias:@probe=./addons/probe/static/src"], odoo_root
    )
    written = esbuild_stubs.write_stubs(stub_root, stubs, *layout)
    return stub_root, src_root, {f"--alias:{spec}": str(path) for spec, path in written}


class TestSecondaryStubMirror(BaseCase):
    FACE = "@probe/core/network"
    NESTED = "@probe/core/network/rpc"
    SIBLING = "@probe/core/network/model_mutation"

    def _build_mirror(self, tmp):
        stub_root, src_root, targets = _build_probe_stub_mirror(
            tmp,
            {
                "core/network.js": "export const face = 'REAL_FACE';",
                "core/network/rpc.js": "export const rpc = 'REAL_RPC';",
                "core/network/model_mutation.js": "export const sub = 'REAL_SUB';",
            },
            {
                self.FACE: "export const face = 'SHIM_FACE';",
                self.NESTED: "export const rpc = 'SHIM_RPC';",
            },
        )
        return stub_root, src_root / "core", targets

    def test_the_alias_target_leaves_room_for_submodules(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub_root, _real, targets = self._build_mirror(tmp)

            target = targets[f"--alias:{self.FACE}"]
            self.assertEqual(target, str(stub_root / "probe" / "core" / "network"))
            self.assertFalse(target.endswith(".js"))
            self.assertEqual(
                (stub_root / "probe/core/network.js").read_text(),
                "export const face = 'SHIM_FACE';",
            )

    def test_an_unstubbed_submodule_still_reaches_the_real_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub_root, _real, _targets = self._build_mirror(tmp)

            mirrored = stub_root / "probe/core/network/model_mutation.js"

            self.assertTrue(mirrored.exists())
            self.assertEqual(mirrored.read_text(), "export const sub = 'REAL_SUB';")

    def test_a_nested_stub_shadows_without_writing_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub_root, real, _targets = self._build_mirror(tmp)

            self.assertEqual(
                (stub_root / "probe/core/network/rpc.js").read_text(),
                "export const rpc = 'SHIM_RPC';",
            )
            self.assertEqual(
                (real / "network" / "rpc.js").read_text(),
                "export const rpc = 'REAL_RPC';",
            )

    @unittest.skipUnless(_get_esbuild_path(), "esbuild binary not available")
    def test_esbuild_resolves_face_and_submodule_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            _stub_root, _real, targets = self._build_mirror(tmp)
            entry = Path(tmp) / "entry.js"
            entry.write_text(
                f"import {{ face }} from '{self.FACE}';\n"
                f"import {{ sub }} from '{self.SIBLING}';\n"
                f"import {{ rpc }} from '{self.NESTED}';\n"
                "console.log(face, sub, rpc);\n"
            )

            proc = subprocess.run(
                [
                    _get_esbuild_path(),
                    str(entry),
                    "--bundle",
                    "--format=esm",
                    "--alias:@probe=./addons/probe/static/src",
                    *(f"{spec}={target}" for spec, target in targets.items()),
                ],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("SHIM_FACE", proc.stdout)
            self.assertIn("REAL_SUB", proc.stdout)
            self.assertIn("SHIM_RPC", proc.stdout)


class TestDeepStubMirror(BaseCase):
    FACE = "@probe/core/network"
    DEEP = "@probe/core/network/plugins/core"

    def _build_mirror(self, tmp):
        stub_root, src_root, _targets = _build_probe_stub_mirror(
            tmp,
            {
                "core/network.js": "export const face = 'REAL_FACE';",
                "core/network/rpc.js": "export const rpc = 'REAL_RPC';",
                "core/network/plugins/core.js": "export const core = 'REAL_DEEP';",
                "core/network/plugins/other.js": "export const other = 'REAL_OTHER';",
            },
            {
                self.FACE: "export const face = 'SHIM_FACE';",
                self.DEEP: "export const core = 'SHIM_DEEP';",
            },
        )
        return stub_root, src_root / "core"

    def test_a_deeply_nested_stub_does_not_overwrite_the_real_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            _stub_root, real = self._build_mirror(tmp)

            self.assertEqual(
                (real / "network" / "plugins" / "core.js").read_text(),
                "export const core = 'REAL_DEEP';",
                "the shim was written through a symlink into the source tree",
            )

    def test_the_deeply_nested_shim_still_lands_in_the_mirror(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub_root, _real = self._build_mirror(tmp)

            self.assertEqual(
                (stub_root / "probe/core/network/plugins/core.js").read_text(),
                "export const core = 'SHIM_DEEP';",
            )

    def test_unstubbed_neighbours_at_every_depth_reach_the_real_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub_root, _real = self._build_mirror(tmp)

            for rel, expected in (
                ("probe/core/network/rpc.js", "export const rpc = 'REAL_RPC';"),
                (
                    "probe/core/network/plugins/other.js",
                    "export const other = 'REAL_OTHER';",
                ),
            ):
                with self.subTest(rel=rel):
                    self.assertEqual((stub_root / rel).read_text(), expected)

    def test_a_write_that_escapes_the_mirror_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub_root = Path(tmp) / "stubs"
            outside = Path(tmp) / "source"
            outside.mkdir()
            stub_root.mkdir()
            (stub_root / "leaked").symlink_to(outside, target_is_directory=True)

            with self.assertRaises(RuntimeError) as caught:
                esbuild_stubs.check_inside_mirror(
                    stub_root / "leaked" / "module.js", stub_root
                )
            self.assertIn("outside the stub mirror", str(caught.exception))


class TestBarePackageStubMirror(BaseCase):
    BARE = "@probe"
    SUB = "@probe/core/network"
    ADDON_ALIAS = "--alias:@probe=./addons/probe/static/src"

    def _build_mirror(self, tmp, stubs=None):
        return _build_probe_stub_mirror(
            tmp,
            {
                "index.js": "export const face = 'REAL_INDEX';",
                "core/network.js": "export const net = 'REAL_NET';",
            },
            stubs or {self.BARE: "export const face = 'SHIM_INDEX';"},
        )

    def test_the_bare_specifier_gets_a_shim_and_an_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub_root, _real, targets = self._build_mirror(tmp)

            self.assertEqual(targets[f"--alias:{self.BARE}"], str(stub_root / "probe"))
            self.assertEqual(
                (stub_root / "probe.js").read_text(),
                "export const face = 'SHIM_INDEX';",
            )

    def test_the_addon_static_src_is_still_reachable_beside_the_shim(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub_root, _real, _targets = self._build_mirror(tmp)

            self.assertEqual(
                (stub_root / "probe" / "core" / "network.js").read_text(),
                "export const net = 'REAL_NET';",
            )

    def test_a_bare_stub_alongside_a_sub_path_stub_writes_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub_root, real, _targets = self._build_mirror(
                tmp,
                stubs={
                    self.BARE: "export const face = 'SHIM_INDEX';",
                    self.SUB: "export const net = 'SHIM_NET';",
                },
            )

            self.assertEqual(
                (stub_root / "probe.js").read_text(),
                "export const face = 'SHIM_INDEX';",
            )
            self.assertEqual(
                (stub_root / "probe" / "core" / "network.js").read_text(),
                "export const net = 'SHIM_NET';",
            )
            self.assertEqual(
                (real / "core" / "network.js").read_text(),
                "export const net = 'REAL_NET';",
            )

    @unittest.skipUnless(_get_esbuild_path(), "esbuild binary not available")
    def test_esbuild_prefers_the_shim_over_the_packages_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            _stub_root, _real, targets = self._build_mirror(tmp)
            entry = Path(tmp) / "entry.js"
            entry.write_text(
                f"import {{ face }} from '{self.BARE}';\n"
                f"import {{ net }} from '{self.SUB}';\n"
                "console.log(face, net);\n"
            )
            stubbed = {key.removeprefix("--alias:") for key in targets}
            alias_flags = [
                flag
                for flag in [self.ADDON_ALIAS]
                if flag.removeprefix("--alias:").partition("=")[0] not in stubbed
            ]

            proc = subprocess.run(
                [
                    _get_esbuild_path(),
                    str(entry),
                    "--bundle",
                    "--format=esm",
                    *alias_flags,
                    *(f"{spec}={target}" for spec, target in targets.items()),
                ],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("SHIM_INDEX", proc.stdout)
            self.assertNotIn("REAL_INDEX", proc.stdout)
            self.assertIn("REAL_NET", proc.stdout)
