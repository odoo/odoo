# Part of Odoo. Reproduction test — no manual/faked HTTP calls.
#
# This test drives the REAL browser UI (res.partner form -> mail chatter
# attachment -> web.FileViewer -> Download button) and only *observes*
# the odoo.http logger. It never constructs the 'token' param itself:
# that field is appended by Odoo's own
# addons/web/static/src/core/network/download.js when the user clicks
# the native Download button. We are only witnesses, not actors.
#
# Requires only 'base', 'web' and 'mail' (all core Odoo, no custom code).

from odoo.tests import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestFileViewerDownloadWarning(HttpCase):
    def test_download_button_triggers_ignoring_args_warning(self):
        # Minimal native setup: a partner + an attachment on its chatter,
        # exactly like any real user attaching a file to a contact.
        partner = self.env["res.partner"].create({"name": "Download Warning Repro"})
        attachment = self.env["ir.attachment"].create(
            {
                "name": "repro.txt",
                "raw": b"hello world",
                "res_model": "res.partner",
                "res_id": partner.id,
                "mimetype": "text/plain",
            },
        )

        partner.message_post(body="Attachment test", attachment_ids=[attachment.id])
        with self.assertLogs("odoo.http", level="WARNING") as log_catcher:
            self.start_tour(
                f"/odoo/res.partner/{partner.id}?debug=1",
                "file_viewer_download_warning_tour",
                login="admin",
            )

        self.assertFalse(
            any(
                "called ignoring args" in line and "token" in line
                for line in log_catcher.output
            ),
            (
                "Unexpected WARNING via download.js from core Odoo's"
                "own FileViewer Download button to trigger "
                "a 'called ignoring args {'token'}', "
                f"but got:\n{log_catcher.output}"
            ),
        )
