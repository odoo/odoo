import logging

from odoo.modules.module import Manifest
from odoo.tests import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestLocatedStatusesTravelWithTheClient(TransactionCase):
    """Wherever a client reads a decorated `im_status`, it must know what a
    located one means.

    `res.partner._compute_presence` decorates `im_status` for every client, not
    only for the backend, so a bundle that renders the member list or the status
    icon without this module's patches puts an employee who is online at their
    desk under Offline, or draws no icon at all for them.
    """

    PARTITIONING_PATH = "mail/static/src/discuss/core/common/thread_model_patch.js"
    STATUS_ICON_PATH = "mail/static/src/core/common/im_status.xml"
    VOCABULARY_PATH = (
        "hr_homeworking/static/src/components/work_location_presence/im_status_patch.js"
    )
    ICON_PATH = "hr_homeworking/static/src/components/work_location_presence/im_status_patch.xml"

    def _bundles_containing(self, path):
        IrAsset = self.env["ir.asset"]
        params = IrAsset._prepare_assets_params()
        installed = set(
            self.env["ir.module.module"]
            .search([("state", "=", "installed")])
            .mapped("name")
        )
        bundles = set(IrAsset.search([]).mapped("bundle"))
        for manifest in Manifest.get_all_addon_manifests():
            if manifest.name in installed:
                bundles.update(manifest.get("assets") or {})
        found = set()
        for bundle in sorted(bundles):
            try:
                entries = IrAsset._get_asset_paths(bundle, params)
            except Exception as exc:
                _logger.info("skipping bundle %s: %s", bundle, exc)
                continue
            if any(entry.path.lstrip("/") == path for entry in entries):
                found.add(bundle)
        return found

    def test_every_bundle_that_partitions_members_knows_the_located_statuses(self):
        partitioning = self._bundles_containing(self.PARTITIONING_PATH)
        self.assertTrue(
            partitioning,
            f"could not find the bundles carrying {self.PARTITIONING_PATH}",
        )
        vocabulary = self._bundles_containing(self.VOCABULARY_PATH)
        missing = partitioning - vocabulary
        self.assertFalse(
            missing,
            f"{sorted(missing)} sort members with mail's onlineMemberStatuses but "
            "never learn that a located status is online, so an employee at their "
            "desk shows as offline there",
        )

    def test_every_bundle_that_draws_the_status_icon_knows_the_located_statuses(self):
        drawing = self._bundles_containing(self.STATUS_ICON_PATH)
        self.assertTrue(
            drawing, f"could not find the bundles carrying {self.STATUS_ICON_PATH}"
        )
        icons = self._bundles_containing(self.ICON_PATH)
        missing = drawing - icons
        self.assertFalse(
            missing,
            f"{sorted(missing)} render mail.ImStatus without this module's "
            "inherit, so a located status draws the unknown-status icon there",
        )
