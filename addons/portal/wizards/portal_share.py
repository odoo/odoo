from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PortalShare(models.TransientModel):
    _name = "portal.share"
    _description = "Portal Sharing"

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        for name, context_key in (
            ("res_model", "active_model"),
            ("res_id", "active_id"),
        ):
            if name in fields_list:
                result.setdefault(name, self.env.context.get(context_key, False))
        return result

    @api.model
    def _selection_target_model(self):
        portal_mixin_cls = self.pool["mixin.portal"]
        portal_model_names = [
            name
            for name, model_cls in self.pool.items()
            if issubclass(model_cls, portal_mixin_cls) and not model_cls._abstract
        ]
        names = dict(
            self.env["ir.model"]
            .sudo()
            .search_fetch([("model", "in", portal_model_names)], ["model", "name"])
            .mapped(lambda m: (m.model, m.name))
        )
        return [(name, names.get(name, name)) for name in portal_model_names]

    res_model = fields.Char(
        string="Related Document Model",
        required=True,
    )
    res_id = fields.Integer(
        string="Related Document ID",
        required=True,
    )
    resource_ref = fields.Reference(
        selection="_selection_target_model",
        string="Related Document",
        compute="_compute_resource_ref",
    )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Recipients",
        required=True,
    )
    note = fields.Text(help="Add extra content to display in the email")
    share_link = fields.Char(
        string="Link",
        compute="_compute_share_link",
    )
    access_warning = fields.Text(
        string="Access warning",
        compute="_compute_access_warning",
    )

    @api.depends("res_model", "res_id")
    def _compute_resource_ref(self):
        for wizard in self:
            record = wizard._get_portal_record()
            wizard.resource_ref = f"{record._name},{record.id}" if record else False

    def _get_portal_record(self):
        self.check_singleton()
        empty = self.env["mixin.portal"]
        if not self.res_model or self.res_model not in self.env:
            return empty
        res_model = self.env[self.res_model]
        if (
            not res_model._abstract
            and isinstance(res_model, self.pool["mixin.portal"])
            and self.res_id
        ):
            return res_model.browse(self.res_id).exists()
        return empty

    @api.depends("res_model", "res_id")
    def _compute_share_link(self):
        for rec in self:
            record = rec._get_portal_record()
            rec.share_link = (
                record.get_base_url() + record._get_share_url(redirect=True)
                if record
                else False
            )

    @api.depends("res_model", "res_id")
    def _compute_access_warning(self):
        for rec in self:
            record = rec._get_portal_record()
            rec.access_warning = record.access_warning if record else False

    def _get_shared_record(self):
        self.check_singleton()
        record = self._get_portal_record()
        if not record:
            raise UserError(_("This document cannot be shared: it has no portal page."))
        record.check_access("read")
        return record

    def _post_share_email(self, partner, share_link, *, record=None):
        """Render in the recipient's language, reusing a validated batch target."""
        if record is None:
            record = self._get_shared_record()
        record = record.with_context(lang=partner.lang or self.env.lang)
        record.message_post_with_source(
            "portal.portal_share_template",
            render_values={
                "partner": partner,
                "note": self.note,
                "record": record,
                "share_link": share_link,
                "model_description": record.env["ir.model"]
                ._get(record._name)
                .display_name.lower(),
            },
            subject=record.env._("Invitation to access %s", record.display_name),
            subtype_xmlid="mail.mt_note",
            email_layout_xmlid="mail.mail_notification_light",
            partner_ids=partner.ids,
        )

    def _send_public_link(self, partners=None):
        if partners is None:
            partners = self.partner_ids
        record = self._get_shared_record()
        for partner in partners:
            share_link = record.get_base_url() + record._get_share_url(
                redirect=True, pid=partner.id
            )
            self._post_share_email(partner, share_link, record=record)

    def _send_signup_link(self, partners=None):
        if partners is None:
            partners = self.partner_ids.filtered(lambda partner: not partner.user_ids)
        if not partners:
            return
        record = self._get_shared_record()
        for partner in partners:
            partner.signup_get_auth_param()
            share_link = partner._get_signup_url_for_action(
                action="/mail/view", res_id=self.res_id, model=self.res_model
            )[partner.id]
            self._post_share_email(partner, share_link, record=record)

    def _get_public_link_partners(self):
        self.check_singleton()
        signup_enabled = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("auth_signup.invitation_scope")
            == "b2c"
        )
        if not signup_enabled:
            return self.partner_ids
        return self.partner_ids.filtered(lambda partner: partner.user_ids)

    def action_send_mail(self):
        self.check_singleton()
        self._get_shared_record()
        public_link_partners = self._get_public_link_partners()
        self._send_public_link(public_link_partners)
        self._send_signup_link(self.partner_ids - public_link_partners)

        return {"type": "ir.actions.act_window_close"}
