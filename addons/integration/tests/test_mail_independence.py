from odoo.modules.module import get_manifest
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

FORMERLY_THREADED = (
    "integration.exchange",
    "integration.service",
    "credential.credential",
)

MAIL_THREAD_FIELDS = ("message_ids", "message_follower_ids")


@tagged("post_install", "-at_install")
class TestMailIndependence(TransactionCase):
    def test_manifest_does_not_depend_on_mail(self):
        depends = get_manifest("integration")["depends"]
        self.assertNotIn(
            "mail",
            depends,
            "integration is a transport primitive; every module that wants an "
            "HTTP client would pull in mail, web_tour and html_editor with it. "
            "If a chatter is genuinely wanted, put it in a bridge module rather "
            "than in this manifest.",
        )

    def test_transitive_dependencies_do_not_reach_mail(self):
        seen = set()
        queue = ["integration"]
        while queue:
            module = queue.pop()
            if module in seen:
                continue
            seen.add(module)
            queue.extend(get_manifest(module).get("depends", []))

        self.assertNotIn(
            "mail",
            seen,
            f"integration reaches mail transitively through {sorted(seen)}; "
            "dropping it from the manifest alone does not make the module "
            "independent of it.",
        )

    def test_models_carry_no_mail_thread(self):
        for model_name in FORMERLY_THREADED:
            fields = self.env[model_name]._fields
            for field_name in MAIL_THREAD_FIELDS:
                self.assertNotIn(
                    field_name,
                    fields,
                    f"{model_name} has {field_name}, so something re-inherited "
                    "mail.thread. On integration.exchange in particular that is a "
                    "mail.message and a mail.tracking.value per API request, on "
                    "the fastest-growing table this module owns.",
                )

    def test_event_log_tracks_no_field(self):
        tracked = [
            name
            for name, field in self.env["integration.exchange"]._fields.items()
            if getattr(field, "tracking", False)
        ]
        self.assertFalse(
            tracked,
            f"integration.exchange tracks {tracked}. Tracking writes a mail.message per "
            "state transition, and this model records one row per API request.",
        )
