import collections
import io
import pathlib
import re
import zipfile

from odoo.modules.module import Manifest
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestHandlerShipping(HttpCase):
    """``/iot/get_handlers`` decides which driver files reach a box.

    Which module ships a driver is a manifest property since the driver split,
    so these pin the two keys rather than a list of module names.
    """

    def _box(self, version="L25.07", auto_update=True):
        return (
            self.env["iot.box"]
            .sudo()
            .create(
                {
                    "name": "Handler Box",
                    "identifier": "handler-box",
                    "ip": "10.0.0.4",
                    "version": version,
                    "drivers_auto_update": auto_update,
                }
            )
        )

    def _fetch(self, identifier="handler-box", auto="False"):
        return self.url_open(f"/iot/get_handlers?identifier={identifier}&auto={auto}")

    def _names(self, response):
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            return set(zf.namelist())

    def test_the_box_firmware_handlers_always_ship(self):
        self._box()
        names = self._names(self._fetch())
        self.assertIn("drivers/printer_driver_base.py", names)
        self.assertIn("interfaces/serial_interface.py", names)

    def test_a_driver_that_must_always_be_present_installs_itself(self):
        """The box has to report a fiscal data module before anyone installs the
        app that acts on one, and the database has to be able to READ what it
        reports. Shipping the driver without installing its module gives the
        first and not the second: the error codes and the device subtype are
        named only by that module. ``iot_blackbox_be`` is ``auto_install`` on
        ``iot`` so both hold."""
        self.assertEqual(
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", "iot_blackbox_be")], limit=1)
            .state,
            "installed",
            "iot_blackbox_be should have auto-installed alongside iot",
        )
        self._box()
        self.assertIn("drivers/serial_blackbox_driver.py", self._names(self._fetch()))

    def test_an_uninstalled_driver_without_that_key_does_not_ship(self):
        self._box()
        self.assertNotIn("drivers/adam_scale_driver.py", self._names(self._fetch()))

    def test_a_dated_image_is_not_sent_what_it_already_carries(self):
        """A dated box builds its handlers from git. Re-sending them would
        overwrite the git copy with the database's."""
        self._box(version="2025.09.01")
        names = self._names(self._fetch())
        self.assertNotIn("drivers/serial_blackbox_driver.py", names)
        self.assertNotIn("drivers/IngenicoDriver.py", names)
        self.assertIn(
            "drivers/serial_base_driver.py",
            names,
            "the driver framework ships to a dated box too: withholding a "
            "module deletes its handlers on the box rather than preserving "
            "them, and a box without iot_drivers has no drivers at all",
        )

    def test_a_windows_box_is_not_sent_linux_handlers(self):
        self._box(version="W25.07")
        names = self._names(self._fetch())
        self.assertFalse(
            [n for n in names if n.endswith("_L.py")],
            "a Windows box must not receive Linux-only handlers",
        )

    def test_a_linux_box_is_not_sent_windows_handlers(self):
        self._box(version="L25.07")
        names = self._names(self._fetch())
        self.assertFalse([n for n in names if n.endswith("_W.py")])

    def test_an_unknown_box_gets_nothing(self):
        self.assertEqual(self._fetch(identifier="no-such-box").status_code, 404)

    def test_auto_update_off_refuses_an_automatic_request(self):
        self._box(auto_update=False)
        self.assertEqual(self._fetch(auto="True").status_code, 401)
        self.assertEqual(
            self._fetch(auto="False").status_code,
            200,
            "a hand-triggered update is still allowed",
        )


@tagged("post_install", "-at_install")
class TestHandlerNamespace(HttpCase):
    def test_no_two_modules_claim_the_same_handler_path(self):
        """Handlers land flat on the box, so the path inside the zip is the
        whole namespace.

        Before the driver split one module owned the payment terminals and a
        clash was local to it. Nine modules contribute now, ``zipfile`` accepts
        a duplicate name without complaint, and extraction keeps whichever was
        written last -- so a collision would be decided by module ordering and
        report nothing. This is the model-name-ownership question one layer
        down.
        """
        owners = collections.defaultdict(list)
        for manifest in Manifest.get_all_addon_manifests():
            handlers = pathlib.Path(manifest.path) / "iot_handlers"
            if not handlers.is_dir():
                continue
            for handler in handlers.glob("*/*"):
                if handler.name.startswith((".", "_")):
                    continue
                owners[f"{handler.parent.name}/{handler.name}"].append(manifest.name)

        self.assertTrue(owners, "the scan reached no handlers at all")
        clashes = {path: mods for path, mods in owners.items() if len(mods) > 1}
        self.assertFalse(
            clashes,
            "these handler paths are claimed by more than one module, and the "
            "box would silently keep one of them: %s" % clashes,
        )


@tagged("post_install", "-at_install")
class TestHandlerDependencies(HttpCase):
    """A handler that imports another handler needs both in the same zip.

    Before the driver split one module shipped the payment terminals and their
    shared base together, so the question could not arise. Nine modules ship
    them now and the edges cross module boundaries, while the import path is
    ``odoo.addons.iot_drivers.iot_handlers.*`` whoever shipped the file -- so
    the import reads as internal and is not.
    """

    _IMPORT = re.compile(r"odoo\.addons\.iot_drivers\.iot_handlers\.(\w+)\.(\w+)")

    def _shippers(self):
        """handler path -> the module that ships it, and each module's manifest."""
        ships, manifests = {}, {}
        for manifest in Manifest.get_all_addon_manifests():
            handlers = pathlib.Path(manifest.path) / "iot_handlers"
            if not handlers.is_dir():
                continue
            manifests[manifest.name] = manifest
            for handler in handlers.glob("*/*.py"):
                if handler.name.startswith(("_", ".")):
                    continue
                ships[f"{handler.parent.name}.{handler.stem}"] = manifest.name
        return ships, manifests

    def _edges(self, ships):
        """(importer, provider, handler) for every cross-module handler import."""
        edges = set()
        for manifest in Manifest.get_all_addon_manifests():
            handlers = pathlib.Path(manifest.path) / "iot_handlers"
            if not handlers.is_dir():
                continue
            for handler in handlers.glob("*/*.py"):
                for kind, name in self._IMPORT.findall(handler.read_text()):
                    provider = ships.get(f"{kind}.{name}")
                    if provider and provider != manifest.name:
                        edges.add((manifest.name, provider, f"{kind}/{name}.py"))
        return edges

    def _closure(self, name, seen=None):
        seen = seen if seen is not None else set()
        manifest = Manifest.for_addon(name, display_warning=False)
        for dep in manifest["depends"] if manifest else []:
            if dep not in seen:
                seen.add(dep)
                self._closure(dep, seen)
        return seen

    def test_a_handler_never_imports_one_its_module_cannot_guarantee(self):
        ships, _manifests = self._shippers()
        edges = self._edges(ships)
        self.assertTrue(edges, "the scan found no cross-module handler imports")

        broken = []
        for importer, provider, handler in sorted(edges):
            if provider == "iot_drivers":
                continue  # shipped unconditionally by the controller
            if provider not in self._closure(importer):
                broken.append(f"{importer} imports {handler} from {provider}")
        self.assertFalse(
            broken,
            "these modules ship a handler importing another module's handler "
            "without depending on it, so the box can receive one without the "
            "other: %s" % broken,
        )

    def test_a_dated_image_never_drops_a_provider_and_keeps_its_importer(self):
        """``iot_handlers_in_image`` withholds a module's handlers from a dated
        box. Withholding a provider while still sending its importer would ship
        an import of a file that is not there."""
        ships, manifests = self._shippers()
        broken = []
        for importer, provider, handler in sorted(self._edges(ships)):
            if provider == "iot_drivers":
                continue
            if (
                manifests[provider]["iot_handlers_in_image"]
                and not manifests[importer]["iot_handlers_in_image"]
            ):
                broken.append(f"{importer} keeps {handler}, but {provider} is withheld")
        self.assertFalse(
            broken,
            "a dated box would receive these handlers without what they "
            "import: %s" % broken,
        )


@tagged("post_install", "-at_install")
class TestDeviceTypesAreReadable(HttpCase):
    def test_every_device_type_the_box_can_report_can_also_be_read(self):
        """A driver that ships must also be installed, or the server sees a
        device it cannot interpret.

        The registry entry that names a device's error codes lives in the same
        module as its driver. When the driver shipped to the box without its
        module being installed, a fiscal data module reporting a failure inside
        its response body was read as a success, because the `normalize` hook
        that rewrites such an event was not loaded.
        """
        backend = [
            asset.path
            for asset in self.env["ir.asset"]._get_asset_paths("web.assets_backend", {})
        ]
        self.assertTrue(
            any("fdm_messages" in path for path in backend),
            "iot_blackbox_be registers how a fiscal data module's events are "
            "read; without it in the bundle an error in the response body is "
            "reported to the user as a success",
        )
