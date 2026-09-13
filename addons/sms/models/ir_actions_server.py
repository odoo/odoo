from odoo import _, api, fields, models


class IrActionsServer(models.Model):
    """Add SMS option in server actions."""

    _inherit = "ir.actions.server"

    state = fields.Selection(
        selection_add=[
            ("sms", "Send SMS"),
            ("followers",),
        ],
        ondelete={"sms": "cascade"},
    )
    # SMS
    sms_template_id = fields.Many2one(
        comodel_name="sms.template",
        string="SMS Template",
        compute="_compute_sms_template_id",
        store=True,
        readonly=False,
        domain="[('model_id', '=', model_id)]",
        ondelete="set null",
    )
    sms_method = fields.Selection(
        selection=[
            ("sms", "SMS (without note)"),
            ("comment", "SMS (with note)"),
            ("note", "Note only"),
        ],
        string="Send SMS As",
        compute="_compute_sms_method",
        store=True,
        readonly=False,
    )

    @api.model
    def _get_states_needing_a_live_record(self):
        return super()._get_states_needing_a_live_record() | {"sms"}

    def _is_batchable(self):
        self.check_singleton()
        return self.state == "sms" or super()._is_batchable()

    @api.model
    def _get_fields_name_depends(self):
        return [*super()._get_fields_name_depends(), "sms_template_id"]

    def _prepare_automated_name(self):
        self.check_singleton()
        if self.state == "sms" and self.sms_template_id:
            return _("Send %(template_name)s", template_name=self.sms_template_id.name)
        return super()._prepare_automated_name()

    @api.depends("state")
    def _compute_available_model_ids(self):
        # Narrow what the modules below offer; never replace it. Assigning the
        # whole search result for `sms` actions dropped base's own filtering --
        # the models the reader may access -- and would drop any narrowing a
        # module in between had applied, silently and only for this state.
        super()._compute_available_model_ids()
        sms_based = self.filtered(lambda action: action.state == "sms")
        if not sms_based:
            return
        supported = set(
            self.env["ir.model"]
            .search(
                [
                    ("is_mail_thread", "=", True),
                    ("transient", "=", False),
                ]
            )
            ._ids
        )
        for action in sms_based:
            action.available_model_ids = [
                model_id
                for model_id in action.available_model_ids._ids
                if model_id in supported
            ]

    @api.depends("model_id", "state")
    def _compute_sms_template_id(self):
        to_reset = self.filtered(
            lambda act: (
                act.state != "sms" or (act.model_id != act.sms_template_id.model_id)
            )
        )
        if to_reset:
            to_reset.sms_template_id = False

    @api.depends("state")
    def _compute_sms_method(self):
        # Seed the default, never impose it. The ORM marks a dependent modified
        # on any write naming a dependency -- a write of the same value included
        # -- so assigning 'sms' on every pass turned an action configured to
        # only log a note into one that sends the message for real, on nothing
        # more than an export and re-import of the record.
        for action in self:
            if action.state != "sms":
                action.sms_method = False
            elif not action.sms_method:
                action.sms_method = "sms"

    @api.model
    def _get_fields_warning_depends(self):
        return super()._get_fields_warning_depends() + [
            "model_id",
            "state",
            "sms_template_id",
        ]

    def _get_warning_messages(self):
        self.check_singleton()
        warnings = super()._get_warning_messages()

        if self.state == "sms":
            if self.model_id.transient or not self.model_id.is_mail_thread:
                warnings.append(
                    _(
                        "Sending SMS can only be done on a not transient mixin.mail.thread model"
                    )
                )

            if self.sms_template_id and self.sms_template_id.model_id != self.model_id:
                warnings.append(
                    _(
                        "SMS template model of %(action_name)s does not match action model.",
                        action_name=self.name,
                    )
                )

        return warnings

    def _run_action_sms_multi(self, eval_context=None):
        records = eval_context.get("records") or eval_context.get("record")
        if records:
            # per record, not for the set: the composer below takes the whole
            # batch, and one record still waiting on a recompute must not stop
            # the message going out for the others
            records -= self._get_recompute_pending(records)
        if not self.sms_template_id or not records:
            return False

        composer = (
            self.env["sms.composer"]
            .with_context(
                default_res_model=records._name,
                default_res_ids=records.ids,
                default_composition_mode="comment"
                if self.sms_method == "comment"
                else "mass",
                default_template_id=self.sms_template_id.id,
                default_mass_keep_log=self.sms_method == "note",
            )
            .create({})
        )
        composer.action_send_sms()
        return False
