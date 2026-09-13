import base64
import pathlib
import tempfile
import textwrap
from unittest.mock import patch

import lxml

from odoo.tests.common import BaseCase, TransactionCase, tagged
from odoo.tools import mute_logger
from odoo.tools.misc import file_path

from .common import AddonManifestPatched
from odoo.addons.base.models.ir_asset_paths import (
    AssetDirectiveError,
    AssetPaths,
    _get_static_files,
)


class TestAddonPaths(BaseCase):
    def test_operations(self):
        asset_paths = AssetPaths()
        self.assertFalse(asset_paths.list)

        asset_paths.append_paths(
            [
                ("/home/user/odoo/addons/web/a", "/web/a", 1),
                ("/home/user/odoo/addons/web/c", "/web/c", 1),
                ("/home/user/odoo/addons/web/d", "/web/d", 1),
            ],
            "bundle1",
        )
        self.assertEqual(
            asset_paths.list,
            [
                ("/home/user/odoo/addons/web/a", "/web/a", "bundle1", 1),
                ("/home/user/odoo/addons/web/c", "/web/c", "bundle1", 1),
                ("/home/user/odoo/addons/web/d", "/web/d", "bundle1", 1),
            ],
        )

        asset_paths.append_paths(
            [
                ("/home/user/odoo/addons/web/c", "/web/c", 1),
                ("/home/user/odoo/addons/web/f", "/web/f", 1),
            ],
            "bundle2",
        )
        self.assertEqual(
            asset_paths.list,
            [
                ("/home/user/odoo/addons/web/a", "/web/a", "bundle1", 1),
                ("/home/user/odoo/addons/web/c", "/web/c", "bundle1", 1),
                ("/home/user/odoo/addons/web/d", "/web/d", "bundle1", 1),
                ("/home/user/odoo/addons/web/f", "/web/f", "bundle2", 1),
            ],
        )

        asset_paths.insert_paths(
            [
                ("/home/user/odoo/addons/web/c", "/web/c", 1),
                ("/home/user/odoo/addons/web/e", "/web/e", 1),
            ],
            "bundle3",
            3,
        )
        self.assertEqual(
            asset_paths.list,
            [
                ("/home/user/odoo/addons/web/a", "/web/a", "bundle1", 1),
                ("/home/user/odoo/addons/web/c", "/web/c", "bundle1", 1),
                ("/home/user/odoo/addons/web/d", "/web/d", "bundle1", 1),
                ("/home/user/odoo/addons/web/e", "/web/e", "bundle3", 1),
                ("/home/user/odoo/addons/web/f", "/web/f", "bundle2", 1),
            ],
        )

        asset_paths.insert_paths(
            [
                ("/home/user/odoo/addons/web/b", "/web/b", 1),
                ("/home/user/odoo/addons/web/d", "/web/d", 1),
            ],
            "bundle4",
            1,
        )
        self.assertEqual(
            asset_paths.list,
            [
                ("/home/user/odoo/addons/web/a", "/web/a", "bundle1", 1),
                ("/home/user/odoo/addons/web/b", "/web/b", "bundle4", 1),
                ("/home/user/odoo/addons/web/c", "/web/c", "bundle1", 1),
                ("/home/user/odoo/addons/web/d", "/web/d", "bundle1", 1),
                ("/home/user/odoo/addons/web/e", "/web/e", "bundle3", 1),
                ("/home/user/odoo/addons/web/f", "/web/f", "bundle2", 1),
            ],
        )

        asset_paths.remove_paths(
            [
                ("/home/user/odoo/addons/web/c", "/web/c", 1),
                ("/home/user/odoo/addons/web/d", "/web/d", 1),
                ("/home/user/odoo/addons/web/g", "/web/g", 1),
            ],
            "bundle5",
        )
        self.assertEqual(
            asset_paths.list,
            [
                ("/home/user/odoo/addons/web/a", "/web/a", "bundle1", 1),
                ("/home/user/odoo/addons/web/b", "/web/b", "bundle4", 1),
                ("/home/user/odoo/addons/web/e", "/web/e", "bundle3", 1),
                ("/home/user/odoo/addons/web/f", "/web/f", "bundle2", 1),
            ],
        )

    def test_replace_empty_source(self):
        asset_paths = AssetPaths()
        asset_paths.append_paths(
            [
                ("/web/a.js", "/full/a.js", 1),
                ("/web/b.js", "/full/b.js", 1),
                ("/web/c.js", "/full/c.js", 1),
            ],
            "bundle1",
        )
        target_index = asset_paths.get_index_of_first(["/web/b.js"], "bundle1")
        asset_paths.insert_paths([], "bundle1", target_index)
        asset_paths.remove_paths([("/web/b.js", "/full/b.js", 1)], "bundle1")

        self.assertEqual(len(asset_paths.list), 2)
        self.assertEqual(asset_paths.list[0][0], "/web/a.js")
        self.assertEqual(asset_paths.list[1][0], "/web/c.js")
        self.assertNotIn("/web/b.js", asset_paths.memo)

    def test_glob_static_file_race_condition(self):
        with tempfile.TemporaryDirectory() as tmp:
            static_dir = str(pathlib.Path(tmp).resolve())
            deleted_file = f"{static_dir}/_test_asset_race_condition.js"
            with patch(
                "odoo.addons.base.models.ir_asset_paths.glob",
                return_value=[deleted_file],
            ):
                result = _get_static_files(f"{static_dir}/*.js", static_dir)
        self.assertEqual(result, [], "Deleted files should be silently skipped")

    def test_glob_static_file_filters_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            static_dir = str(pathlib.Path(tmp).resolve())
            for name in ("file.js", "file.py", "file.css"):
                pathlib.Path(static_dir, name).write_text("", encoding="utf-8")
            result = _get_static_files(f"{static_dir}/*", static_dir)
        paths = [r[0] for r in result]
        self.assertIn(f"{static_dir}/file.js", paths)
        self.assertIn(f"{static_dir}/file.css", paths)
        self.assertNotIn(f"{static_dir}/file.py", paths)

    @mute_logger(
        "odoo.addons.base.models.ir_asset",
        "odoo.addons.base.models.ir_asset_paths",
    )
    def test_glob_static_file_memo_is_not_shared_across_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root_a = pathlib.Path(tmp, "a", "static")
            root_b = pathlib.Path(tmp, "b", "static")
            (root_a / "src").mkdir(parents=True)
            root_b.mkdir(parents=True)
            (root_a / "src" / "in_a.js").write_text("var a;")
            (root_b / "in_b.js").write_text("var b;")

            memo = {}
            found_a = _get_static_files(f"{root_a}/**/*.js", str(root_a), memo)
            found_b = _get_static_files(f"{root_b}/*.js", str(root_b), memo)

        self.assertEqual([pathlib.Path(f).name for f, _mtime in found_a], ["in_a.js"])
        self.assertEqual([pathlib.Path(f).name for f, _mtime in found_b], ["in_b.js"])

    def test_glob_static_file_drops_matches_linking_out_of_static(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            static_dir = root / "static"
            (static_dir / "src").mkdir(parents=True)
            (static_dir / "src" / "inside.js").write_text("")
            outside = root / "outside"
            outside.mkdir()
            (outside / "secret.js").write_text("")
            (static_dir / "escape").symlink_to(outside)

            result = _get_static_files(f"{static_dir}/*/*.js", str(static_dir))

        self.assertEqual(
            [path for path, _mtime in result], [f"{static_dir}/src/inside.js"]
        )


class TestParseBundleName(TransactionCase):
    def test_no_extension(self):
        IrAsset = self.env["ir.asset"]
        with self.assertRaises(ValueError) as cm:
            IrAsset._parse_bundle_name("nodotfilename", debug_assets=True)
        self.assertIn("no extension", str(cm.exception))
        self.assertIn("nodotfilename", str(cm.exception))

    def test_valid_debug_js(self):
        IrAsset = self.env["ir.asset"]
        name, rtl, asset_type, autoprefix = IrAsset._parse_bundle_name(
            "web.assets_frontend.js", debug_assets=True
        )
        self.assertEqual(name, "web.assets_frontend")
        self.assertEqual(asset_type, "js")
        self.assertFalse(rtl)
        self.assertFalse(autoprefix)

    def test_valid_min_css_rtl_autoprefixed(self):
        IrAsset = self.env["ir.asset"]
        name, rtl, asset_type, autoprefix = IrAsset._parse_bundle_name(
            "web.assets_frontend.rtl.autoprefixed.min.css", debug_assets=False
        )
        self.assertEqual(name, "web.assets_frontend")
        self.assertEqual(asset_type, "css")
        self.assertTrue(rtl)
        self.assertTrue(autoprefix)

    def test_unsupported_extension(self):
        IrAsset = self.env["ir.asset"]
        with self.assertRaises(ValueError) as cm:
            IrAsset._parse_bundle_name("web.assets.xml", debug_assets=True)
        self.assertIn("Only js and css", str(cm.exception))


@tagged("assets_manifest")
class TestAssetsManifest(AddonManifestPatched):
    def make_asset_view(self, asset_key, t_call_assets_attrs=None):
        default_attrs = {
            "t-js": "true",
            "t-css": "false",
        }
        if t_call_assets_attrs:
            default_attrs.update(t_call_assets_attrs)

        attrs = " ".join(['%s="%s"' % (k, v) for k, v in default_attrs.items()])
        arch = """
            <div>
                <t t-call-assets="%(asset_key)s" %(attrs)s />
            </div>
        """ % {"asset_key": asset_key, "attrs": attrs}

        return self.env["ir.ui.view"].create(
            {
                "name": "test asset",
                "arch": arch,
                "type": "qweb",
            }
        )

    JS_FIXTURES = {1: "var a=1;", 2: "var b=2;", 3: "var c=3;", 4: "var d=4;"}

    def assertBundleJs(self, bundle, *indexes):
        expected = ";\n\n".join(
            f"/* /test_assetsbundle/static/src/js/test_jsfile{i}.js */\n"
            f"{self.JS_FIXTURES[i]}"
            for i in indexes
        )
        self.assertEqual(bundle.js().raw.decode().strip(), expected.strip())

    def declare_sibling_module(self, assets):
        self.installed_modules.add("test_other")
        self.manifests["test_other"] = {
            "name": "test_other",
            "depends": ["test_assetsbundle"],
            "addons_path": pathlib.Path(__file__).resolve().parent,
            "assets": assets,
        }

    def assertStringEqual(self, reference, tested):
        tested = textwrap.dedent(tested).strip()
        reference = reference.strip()
        self.assertEqual(tested, reference)

    def test_01_globmanifest(self):
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest1")
        self.assertBundleJs(bundle, 1, 2, 3, 4)

    def test_02_globmanifest_no_duplicates(self):
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest2")
        self.assertBundleJs(bundle, 1, 2, 3, 4)

    def test_03_globmanifest_file_before(self):
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest3")
        self.assertBundleJs(bundle, 3, 1, 2, 4)

    def test_04_globmanifest_with_irasset(self):
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "bundle": "test_assetsbundle.manifest4",
                "path": "test_assetsbundle/static/src/js/test_jsfile1.js",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest4")
        self.assertBundleJs(bundle, 3, 1)

    def test_05_only_irasset(self):
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "bundle": "test_assetsbundle.irasset1",
                "path": "test_assetsbundle/static/src/js/test_jsfile1.js",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.irasset1")
        attach = bundle.js()

        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            """
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;
            """,
        )

    def test_06_1_replace(self):
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "bundle": "test_assetsbundle.manifest1",
                "directive": "replace",
                "target": "test_assetsbundle/static/src/js/test_jsfile1.js",
                "path": "http://external.link/external.js",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest1")
        scripts = [link for link in bundle.get_links() if link.endswith("js")]
        self.assertEqual(len(scripts), 2)
        self.assertEqual(scripts[0], "http://external.link/external.js")
        attach = bundle.js()
        self.assertEqual(scripts[1], attach.url)
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            """
            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;;

            /* /test_assetsbundle/static/src/js/test_jsfile4.js */
            var d=4;
            """,
        )

    def test_06_2_replace(self):
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "bundle": "test_assetsbundle.manifest4",
                "directive": "replace",
                "path": "test_assetsbundle/static/src/js/test_jsfile1.js",
                "target": "test_assetsbundle/static/src/js/test_jsfile3.js",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest4")
        attach = bundle.js()
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            """
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;
            """,
        )

    def test_06_3_replace_globs(self):
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "directive": "prepend",
                "bundle": "test_assetsbundle.manifest4",
                "path": "test_assetsbundle/static/src/js/test_jsfile4.js",
            }
        )
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "bundle": "test_assetsbundle.manifest4",
                "directive": "replace",
                "path": "test_assetsbundle/static/src/js/test_jsfile[12].js",
                "target": "test_assetsbundle/static/src/js/test_jsfile[45].js",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest4")
        self.assertBundleJs(bundle, 1, 2, 3)

    def test_07_remove(self):
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "bundle": "test_assetsbundle.manifest5",
                "directive": "remove",
                "path": "test_assetsbundle/static/src/js/test_jsfile2.js",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest5")
        self.assertBundleJs(bundle, 1, 3, 4)

    def test_08_remove_inexistent_file(self):
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "bundle": "test_assetsbundle.remove_error",
                "path": "/test_assetsbundle/static/src/js/test_jsfile1.js",
            }
        )

        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "bundle": "test_assetsbundle.remove_error",
                "directive": "remove",
                "path": "test_assetsbundle/static/src/js/test_doesntexist.js",
            }
        )
        with self.assertRaises(AssetDirectiveError) as cm:
            bundle = self.env["ir.qweb"]._get_asset_bundle(
                "test_assetsbundle.remove_error"
            )
            bundle.js()
        self.assertIn(
            "['test_assetsbundle/static/src/js/test_doesntexist.js'] not found",
            str(cm.exception),
        )

    def test_09_remove_wholeglob(self):
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "bundle": "test_assetsbundle.manifest2",
                "directive": "remove",
                "path": "test_assetsbundle/static/src/*/**",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest2")
        self.assertFalse(bundle.javascripts)
        self.assertFalse(bundle.get_links())

    def test_10_prepend(self):
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "directive": "prepend",
                "bundle": "test_assetsbundle.manifest4",
                "path": "test_assetsbundle/static/src/js/test_jsfile1.js",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest4")
        self.assertBundleJs(bundle, 1, 3)

    def test_11_include(self):
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "directive": "include",
                "bundle": "test_assetsbundle.irasset_include1",
                "path": "test_assetsbundle.manifest6",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle(
            "test_assetsbundle.irasset_include1"
        )
        self.assertBundleJs(bundle, 3)

    def test_12_include2(self):
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest6")
        self.assertBundleJs(bundle, 3)

    def test_13_include_circular(self):
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "directive": "include",
                "bundle": "test_assetsbundle.irasset_include1",
                "path": "test_assetsbundle.irasset_include2",
            }
        )
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "directive": "include",
                "bundle": "test_assetsbundle.irasset_include2",
                "path": "test_assetsbundle.irasset_include1",
            }
        )

        with self.assertRaises(AssetDirectiveError) as cm:
            bundle = self.env["ir.qweb"]._get_asset_bundle(
                "test_assetsbundle.irasset_include1"
            )
            bundle.js()
        self.assertNotIsInstance(cm.exception, RecursionError)
        self.assertIn("Circular assets bundle declaration:", str(cm.exception))

    def test_13_2_include_recursive_sibling(self):
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "directive": "include",
                "bundle": "test_assetsbundle.irasset_include1",
                "path": "test_assetsbundle.irasset_include2",
            }
        )
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "directive": "include",
                "bundle": "test_assetsbundle.irasset_include2",
                "path": "test_assetsbundle.irasset_include3",
            }
        )
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "directive": "include",
                "bundle": "test_assetsbundle.irasset_include2",
                "path": "test_assetsbundle.irasset_include4",
            }
        )
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "directive": "include",
                "bundle": "test_assetsbundle.irasset_include4",
                "path": "test_assetsbundle.irasset_include3",
            }
        )
        self.env["ir.asset"].create(
            {
                "name": "test_jsfile4",
                "bundle": "test_assetsbundle.irasset_include3",
                "path": "test_assetsbundle/static/src/js/test_jsfile1.js",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle(
            "test_assetsbundle.irasset_include1"
        )
        self.assertBundleJs(bundle, 1)

    def test_14_other_module(self):
        self.declare_sibling_module(
            {
                "test_other.mockmanifest1": [
                    ("include", "test_assetsbundle.manifest4"),
                ]
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_other.mockmanifest1")
        self.assertBundleJs(bundle, 3)

    def test_15_other_module_append(self):
        self.declare_sibling_module(
            {
                "test_assetsbundle.manifest4": [
                    "test_assetsbundle/static/src/js/test_jsfile1.js",
                ]
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest4")
        self.assertBundleJs(bundle, 3, 1)

    def test_16_other_module_prepend(self):
        self.declare_sibling_module(
            {
                "test_assetsbundle.manifest4": [
                    (
                        "prepend",
                        "test_assetsbundle/static/src/js/test_jsfile1.js",
                    ),
                ]
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest4")
        self.assertBundleJs(bundle, 1, 3)

    def test_17_other_module_replace(self):
        self.declare_sibling_module(
            {
                "test_assetsbundle.manifest4": [
                    (
                        "replace",
                        "test_assetsbundle/static/src/js/test_jsfile3.js",
                        "test_assetsbundle/static/src/js/test_jsfile1.js",
                    ),
                ]
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest4")
        self.assertBundleJs(bundle, 1)

    def test_17b_other_module_remove(self):
        self.declare_sibling_module(
            {
                "test_assetsbundle.manifest4": [
                    (
                        "remove",
                        "test_assetsbundle/static/src/js/test_jsfile3.js",
                    ),
                    (
                        "append",
                        "test_assetsbundle/static/src/js/test_jsfile1.js",
                    ),
                ]
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest4")
        self.assertBundleJs(bundle, 1)

    def test_18_other_module_external(self):
        self.declare_sibling_module(
            {
                "test_assetsbundle.manifest4": [
                    "http://external.link/external.js",
                ]
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest4")
        scripts = [link for link in bundle.get_links() if link.endswith("js")]
        self.assertEqual(len(scripts), 2)
        self.assertEqual(scripts[0], "http://external.link/external.js")
        self.assertBundleJs(bundle, 3)

    def test_19_css_specific_attrs_in_tcallassets(self):
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.irasset2",
                "path": "http://external.css/externalstyle.css",
            }
        )
        self.env["ir.asset"].create(
            {
                "name": "2",
                "bundle": "test_assetsbundle.irasset2",
                "path": "test_assetsbundle/static/src/css/test_cssfile1.css",
            }
        )
        view = self.make_asset_view(
            "test_assetsbundle.irasset2",
            {
                "t-js": "false",
                "t-css": "true",
                "media": "print",
            },
        )

        rendered = self.env["ir.qweb"]._render(view.id)
        html_tree = lxml.etree.fromstring(rendered)
        stylesheets = html_tree.findall("link")
        self.assertEqual(len(stylesheets), 2)
        self.assertEqual(
            stylesheets[0].get("href"), "http://external.css/externalstyle.css"
        )
        self.assertEqual(stylesheets[0].get("media"), "print")
        self.assertNotEqual(
            stylesheets[1].get("href"), "http://external.css/externalstyle.css"
        )
        self.assertEqual(stylesheets[1].get("media"), "print")

    def test_20_css_base(self):
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.irasset2",
                "path": "http://external.css/externalstyle.css",
            }
        )
        self.env["ir.asset"].create(
            {
                "name": "2",
                "bundle": "test_assetsbundle.irasset2",
                "path": "test_assetsbundle/static/src/scss/test_file1.scss",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.irasset2")
        stylesheets = [link for link in bundle.get_links() if link.endswith("css")]
        self.assertEqual(len(stylesheets), 2)
        attach = bundle.css()
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            """
            /* /test_assetsbundle/static/src/scss/test_file1.scss */
            .rule1{color:#000}
            """,
        )

    def _prefixed_css_content(self):
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.irasset2",
                "path": "test_assetsbundle/static/src/scss/test_prefix.scss",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle(
            "test_assetsbundle.irasset2", js=False, autoprefix=True
        )
        return bundle.css().raw.decode()

    def test_20_css_compatibility_prefix_appearance(self):
        content = self._prefixed_css_content()
        self.assertRegex(
            content,
            r"\.appearance-none\{-webkit-appearance:none;-moz-appearance:none;appearance:none\}",
        )
        self.assertRegex(
            content,
            r"\.appearance-auto\{-webkit-appearance:auto;-moz-appearance:auto;appearance:auto\}",
        )
        self.assertRegex(
            content, r"\.appearance-none-prefixed\{-webkit-appearance:none\}"
        )
        self.assertRegex(
            content,
            r"\.appearance-none-important\{-webkit-appearance:none !important;"
            r"-moz-appearance:none !important;appearance:none !important\}",
        )
        self.assertRegex(
            content,
            r"\.appearance-menulist-button\{-webkit-appearance:menulist-button;"
            r"-moz-appearance:menulist-button;appearance:menulist-button\}",
        )

    def test_20_css_compatibility_prefix_display(self):
        content = self._prefixed_css_content()
        self.assertRegex(content, r"\.display-flex\{display:flex\}")
        self.assertRegex(content, r"\.display-inline-flex\{display:inline-flex\}")
        self.assertRegex(content, r"\.display-inline\{display:inline\}")
        self.assertRegex(content, r"\.display-var-flex\{--dummy-display: flex\}")
        self.assertRegex(
            content,
            r"\.display-var-inline-flex\{--dummy-display: inline-flex\}",
        )
        self.assertRegex(content, r"\.display-var-inline\{--dummy-display: inline\}")

    def test_20_css_compatibility_prefix_flex_flow(self):
        content = self._prefixed_css_content()
        self.assertRegex(content, r"\.flex-flow-row-nowrap\{flex-flow:row nowrap\}")
        self.assertRegex(content, r"\.flex-flow-column-wrap\{flex-flow:column wrap\}")
        self.assertRegex(
            content,
            r"\.flex-flow-column-reverse-wrap-reverse\{flex-flow:column-reverse wrap-reverse\}",
        )
        self.assertRegex(content, r"\.flex-flow-row\{flex-flow:row\}")

    def test_20_css_compatibility_prefix_flex_direction(self):
        content = self._prefixed_css_content()
        self.assertRegex(content, r"\.flex-direction-column\{flex-direction:column\}")
        self.assertRegex(
            content,
            r"\.flex-direction-column-reverse\{flex-direction:column-reverse\}",
        )
        self.assertRegex(content, r"\.flex-direction-row\{flex-direction:row\}")

    def test_20_css_compatibility_prefix_flex_wrap(self):
        content = self._prefixed_css_content()
        self.assertRegex(content, r"\.flex-wrap-wrap\{flex-wrap:wrap\}")
        self.assertRegex(content, r"\.flex-wrap-nowrap\{flex-wrap:nowrap\}")
        self.assertRegex(content, r"\.flex-wrap-wrap-reverse\{flex-wrap:wrap-reverse\}")

    def test_20_css_compatibility_prefix_flex_shorthand(self):
        content = self._prefixed_css_content()
        self.assertRegex(content, r"\.flex-0-0-auto\{flex:0 0 auto\}")
        self.assertRegex(content, r"\.flex-0-1-auto\{flex:0 1 auto\}")
        self.assertRegex(content, r"\.flex-1-1-100\{flex:1 1 100\}")
        self.assertRegex(content, r"\.flex-1-1-100percent\{flex:1 1 100%\}")
        self.assertRegex(content, r"\.flex-auto\{flex:auto\}")
        self.assertRegex(content, r"\.flex-1-30px\{flex:1 30px\}")

    def test_20bis_css_loud_comment_not_mistaken_for_split_marker(self):
        fixture = "test_assetsbundle/static/src/scss/test_split_marker.scss"
        self.assertIn(
            "/*! a1b2c3d */",
            pathlib.Path(file_path(fixture)).read_text(encoding="utf-8"),
            f"{fixture} lost its loud comment; it is the payload, not a comment",
        )
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.irasset_split",
                "path": fixture,
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle(
            "test_assetsbundle.irasset_split", js=False
        )
        content = bundle.css().raw.decode()
        self.assertRegex(content, r"\.split-marker-regression\{color:red\}")
        self.assertIn("/*! a1b2c3d */", content)

    def test_21_js_before_css(self):
        self.declare_sibling_module(
            {
                "test_other.bundle4": [
                    (
                        "before",
                        "test_assetsbundle/static/src/css/test_cssfile1.css",
                        "/test_assetsbundle/static/src/js/test_jsfile4.js",
                    )
                ]
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.bundle4")
        self.assertBundleJs(bundle, 1, 2, 3)

    def test_22_js_before_js(self):
        self.declare_sibling_module(
            {
                "test_assetsbundle.bundle4": [
                    (
                        "before",
                        "/test_assetsbundle/static/src/js/test_jsfile3.js",
                        "/test_assetsbundle/static/src/js/test_jsfile4.js",
                    )
                ]
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.bundle4")
        self.assertBundleJs(bundle, 1, 2, 4, 3)

    def test_23_js_after_css(self):
        self.declare_sibling_module(
            {
                "test_other.bundle4": [
                    (
                        "after",
                        "test_assetsbundle/static/src/css/test_cssfile1.css",
                        "/test_assetsbundle/static/src/js/test_jsfile4.js",
                    )
                ]
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.bundle4")
        self.assertBundleJs(bundle, 1, 2, 3)

    def test_24_js_after_js(self):
        self.declare_sibling_module(
            {
                "test_assetsbundle.bundle4": [
                    (
                        "after",
                        "/test_assetsbundle/static/src/js/test_jsfile2.js",
                        "/test_assetsbundle/static/src/js/test_jsfile4.js",
                    )
                ]
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.bundle4")
        self.assertBundleJs(bundle, 1, 2, 4, 3)

    def test_24_1_before_already_satisfied_does_not_warn(self):
        # jsfile1 already precedes jsfile2 in bundle4: the directive states an
        # ordering that holds, so nothing is stranded
        self.declare_sibling_module(
            {
                "test_assetsbundle.bundle4": [
                    (
                        "before",
                        "/test_assetsbundle/static/src/js/test_jsfile2.js",
                        "/test_assetsbundle/static/src/js/test_jsfile1.js",
                    )
                ]
            }
        )
        with self.assertNoLogs("odoo.addons.base.models.ir_asset_paths", "WARNING"):
            bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.bundle4")
        self.assertBundleJs(bundle, 1, 2, 3)

    def test_24_2_before_violated_by_a_present_file_warns(self):
        self.declare_sibling_module(
            {
                "test_assetsbundle.bundle4": [
                    (
                        "before",
                        "/test_assetsbundle/static/src/js/test_jsfile1.js",
                        "/test_assetsbundle/static/src/js/test_jsfile2.js",
                    )
                ]
            }
        )
        with self.assertLogs(
            "odoo.addons.base.models.ir_asset_paths", "WARNING"
        ) as logs:
            bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.bundle4")
        self.assertIn("NOT repositioned", "\n".join(logs.output))
        self.assertBundleJs(bundle, 1, 2, 3)

    def test_25_js_before_js_in_irasset(self):
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.bundle4",
                "path": "/test_assetsbundle/static/src/js/test_jsfile4.js",
                "target": "/test_assetsbundle/static/src/js/test_jsfile3.js",
                "directive": "before",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.bundle4")
        self.assertBundleJs(bundle, 1, 2, 4, 3)

    def test_26_js_after_js_in_irasset(self):
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.bundle4",
                "path": "/test_assetsbundle/static/src/js/test_jsfile4.js",
                "target": "/test_assetsbundle/static/src/js/test_jsfile2.js",
                "directive": "after",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.bundle4")
        self.assertBundleJs(bundle, 1, 2, 4, 3)

    def test_27_mixing_after_before_js_css_in_irasset(self):
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.bundle4",
                "path": "/test_assetsbundle/static/src/js/test_jsfile4.js",
                "target": "/test_assetsbundle/static/src/css/test_cssfile1.css",
                "directive": "after",
            }
        )
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.bundle4",
                "path": "/test_assetsbundle/static/src/css/test_cssfile3.css",
                "target": "/test_assetsbundle/static/src/js/test_jsfile2.js",
                "directive": "before",
            }
        )
        self.make_asset_view(
            "test_assetsbundle.bundle4",
            {
                "t-js": "true",
                "t-css": "true",
            },
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.bundle4")
        attach_css = bundle.css()
        attach_js = bundle.js()

        js_content = attach_js.raw.decode()
        self.assertStringEqual(
            js_content,
            """
            /* /test_assetsbundle/static/src/js/test_jsfile1.js */
            var a=1;;

            /* /test_assetsbundle/static/src/js/test_jsfile2.js */
            var b=2;;

            /* /test_assetsbundle/static/src/js/test_jsfile4.js */
            var d=4;;

            /* /test_assetsbundle/static/src/js/test_jsfile3.js */
            var c=3;
            """,
        )

        css_content = attach_css.raw.decode()
        self.assertStringEqual(
            css_content,
            """
            /* /test_assetsbundle/static/src/css/test_cssfile3.css */
            .rule4{color: green;}

            /* /test_assetsbundle/static/src/css/test_cssfile1.css */
            .rule1{color: black;}.rule2{color: yellow;}.rule3{color: red;}

            /* /test_assetsbundle/static/src/css/test_cssfile2.css */
            .rule4{color: blue;}
            """,
        )

    def test_28_js_after_js_in_irasset_wrong_path(self):
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.wrong_path",
                "path": "/test_assetsbundle/static/src/js/test_jsfile4.js",
            }
        )
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.wrong_path",
                "path": "/test_assetsbundle/static/src/js/test_jsfile1.js",
                "target": "/test_assetsbundle/static/src/js/doesnt_exist.js",
                "directive": "after",
            }
        )
        with self.assertRaises(AssetDirectiveError) as cm:
            bundle = self.env["ir.qweb"]._get_asset_bundle(
                "test_assetsbundle.wrong_path"
            )
            bundle.js()
        self.assertIn(
            "test_assetsbundle/static/src/js/doesnt_exist.js not found",
            str(cm.exception),
        )

    def test_29_js_after_js_in_irasset_glob(self):
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.manifest4",
                "path": "/test_assetsbundle/static/src/*/**",
                "target": "/test_assetsbundle/static/src/js/test_jsfile3.js",
                "directive": "after",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest4")
        self.assertBundleJs(bundle, 3, 1, 2, 4)

    def test_30_js_before_js_in_irasset_glob(self):
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.manifest4",
                "path": "/test_assetsbundle/static/src/js/test_jsfile[124].js",
                "target": "/test_assetsbundle/static/src/js/test_jsfile3.js",
                "directive": "before",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.manifest4")
        self.assertBundleJs(bundle, 1, 2, 4, 3)

    @mute_logger(
        "odoo.addons.base.models.ir_asset",
        "odoo.addons.base.models.ir_asset_paths",
    )
    def test_31(self):
        path_to_dummy = "../test_assetsbundle/tests/security_dummy.js"
        me = pathlib.Path(__file__).parent.absolute()
        dummy_path = me.joinpath("..", path_to_dummy)
        self.assertTrue(dummy_path.is_file())

        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.irassetsec",
                "path": "/test_assetsbundle/%s" % path_to_dummy,
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.irassetsec")
        with mute_logger("odoo.addons.base.models.assetsbundle"):
            attach = bundle.js()
            self.assertIn(
                b"Could not find /test_assetsbundle/../test_assetsbundle/tests/security_dummy.js",
                attach.exists().raw,
            )

    @mute_logger(
        "odoo.addons.base.models.ir_asset",
        "odoo.addons.base.models.ir_asset_paths",
    )
    def test_32_a_relative_path_in_addon(self):
        path_to_dummy = "../test_assetsbundle/tests/security_dummy.xml"
        me = pathlib.Path(__file__).parent.absolute()
        dummy_path = me.joinpath("..", path_to_dummy)
        self.assertTrue(dummy_path.is_file())

        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.irassetsec",
                "path": "/test_assetsbundle/%s" % path_to_dummy,
            }
        )

        files = self.env["ir.asset"]._get_asset_paths(
            "test_assetsbundle.irassetsec", {}
        )
        self.assertEqual(
            files,
            (
                (
                    "/test_assetsbundle/../test_assetsbundle/tests/security_dummy.xml",
                    None,
                    "test_assetsbundle.irassetsec",
                    None,
                ),
            ),
        )

    @mute_logger(
        "odoo.addons.base.models.ir_asset",
        "odoo.addons.base.models.ir_asset_paths",
    )
    def test_32_b_relative_path_outside_addon(self):
        path_to_dummy = "../test_assetsbundle/tests/security_dummy.xml"
        me = pathlib.Path(__file__).parent.absolute()
        dummy_path = me.joinpath("..", path_to_dummy)
        self.assertTrue(dummy_path.is_file())

        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.irassetsec",
                "path": "%s" % path_to_dummy,
            }
        )
        files = self.env["ir.asset"]._get_asset_paths(
            "test_assetsbundle.irassetsec", {}
        )
        self.assertEqual(
            files,
            (
                (
                    "../test_assetsbundle/tests/security_dummy.xml",
                    None,
                    "test_assetsbundle.irassetsec",
                    None,
                ),
            ),
        )

    def test_33(self):
        self.manifests["notinstalled_module"] = {
            "name": "notinstalled_module",
            "depends": ["test_assetsbundle"],
            "addons_path": pathlib.Path(__file__).resolve().parent,
        }
        self.env["ir.asset"].create(
            {
                "name": "control",
                "bundle": "test_assetsbundle.irassetsec",
                "path": "/test_assetsbundle/static/src/js/test_jsfile1.js",
            }
        )
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.irassetsec",
                "path": "/notinstalled_module/somejsfile.js",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.irassetsec")
        content = (bundle.js().exists().raw or b"").decode()
        self.assertIn("var a=1", content, "the installed member must survive")
        self.assertNotIn("notinstalled_module", content)

    def test_33bis_notinstalled_not_in_manifests(self):
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.irassetsec",
                "path": "/notinstalled_module/somejsfile.js",
            }
        )
        self.make_asset_view("test_assetsbundle.irassetsec")
        attach = self.env["ir.attachment"].search(
            [("name", "ilike", "test_assetsbundle.irassetsec")],
            order="create_date DESC",
            limit=1,
        )
        self.assertFalse(attach.exists())

    @mute_logger(
        "odoo.addons.base.models.ir_asset",
        "odoo.addons.base.models.ir_asset_paths",
    )
    def test_34(self):
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.irassetsec",
                "path": "/test_assetsbundle/__manifest__.py",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle("test_assetsbundle.irassetsec")
        links = bundle.get_links()
        self.assertFalse(links)

    @mute_logger(
        "odoo.addons.base.models.ir_asset",
        "odoo.addons.base.models.ir_asset_paths",
    )
    def test_35(self):
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.irassetsec",
                "path": "/test_assetsbundle/data/ir_asset.xml",
            }
        )
        files = self.env["ir.asset"]._get_asset_paths(
            "test_assetsbundle.irassetsec", {}
        )
        self.assertEqual(
            files,
            (
                (
                    "/test_assetsbundle/data/ir_asset.xml",
                    None,
                    "test_assetsbundle.irassetsec",
                    None,
                ),
            ),
        )

    def test_36(self):
        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.irassetsec",
                "path": "/test_assetsbundle/static/accessible.xml",
            }
        )
        files = self.env["ir.asset"]._get_asset_paths(
            "test_assetsbundle.irassetsec", {}
        )
        modified = files[0][3]

        base_path = str(pathlib.Path(__file__).resolve().parent.parent)

        self.assertEqual(
            files,
            (
                (
                    "/test_assetsbundle/static/accessible.xml",
                    f"{base_path}/static/accessible.xml",
                    "test_assetsbundle.irassetsec",
                    modified,
                ),
            ),
        )

    def test_37_path_can_be_an_attachment(self):
        scss_code = base64.b64encode(b"""
            .my_div {
                &.subdiv {
                    color: blue;
                }
            }
        """)
        self.env["ir.attachment"].create(
            {
                "name": "my custom scss",
                "mimetype": "text/scss",
                "type": "binary",
                "url": "test_assetsbundle/my_style_attach.scss",
                "datas": scss_code,
            }
        )

        self.env["ir.asset"].create(
            {
                "name": "1",
                "bundle": "test_assetsbundle.irasset_custom_attach",
                "path": "test_assetsbundle/my_style_attach.scss",
            }
        )
        bundle = self.env["ir.qweb"]._get_asset_bundle(
            "test_assetsbundle.irasset_custom_attach"
        )
        attach = bundle.css()
        content = attach.raw.decode()
        self.assertStringEqual(
            content,
            """
            /* test_assetsbundle/my_style_attach.scss */
            .my_div.subdiv{color:blue}
            """,
        )
