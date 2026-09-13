from markupsafe import Markup

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    odoobot_state = fields.Selection(
        selection=[
            ("not_initialized", "Not initialized"),
            ("onboarding_emoji", "Onboarding emoji"),
            ("onboarding_attachment", "Onboarding attachment"),
            ("onboarding_command", "Onboarding command"),
            ("onboarding_ping", "Onboarding ping"),
            ("onboarding_canned", "Onboarding canned"),
            ("idle", "Idle"),
            ("disabled", "Disabled"),
        ],
        string="OdooBot Status",
        readonly=True,
    )
    odoobot_failed = fields.Boolean(readonly=True)
    odoobot_canned_response_id = fields.Many2one(
        comodel_name="mail.canned.response",
        string="OdooBot Onboarding Canned Response",
        readonly=True,
        ondelete="set null",
        help="The throw-away canned response created for the onboarding tour, "
        "removed once the user has tried it.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["odoobot_state"]

    def _on_webclient_bootstrap(self):
        super()._on_webclient_bootstrap()
        if self._is_internal() and self.odoobot_state in [False, "not_initialized"]:
            self._init_odoobot()

    def _init_odoobot(self):
        self.check_singleton()
        odoobot = self.env["mail.bot"]._get_odoobot()
        channel = self.env["discuss.channel"]._get_or_create_chat(
            [odoobot.id, self.partner_id.id]
        )
        message = Markup(
            '%s<br/>%s<br/><b>%s</b> <span class="o_odoobot_command">:)</span>'
        ) % (
            self.env._("Hello,"),
            self.env._(
                "Odoo's chat helps employees collaborate efficiently. I'm here to help you discover its features."
            ),
            self.env._("Try to send me an emoji"),
        )
        channel.sudo().message_post(
            author_id=odoobot.id,
            body=message,
            message_type="comment",
            silent=True,
            subtype_xmlid="mail.mt_comment",
        )
        self.sudo().odoobot_state = "onboarding_emoji"
        return channel
