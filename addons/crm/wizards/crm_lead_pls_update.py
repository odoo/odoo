from odoo import fields, models


class CrmLeadPlsUpdate(models.TransientModel):
    _name = "crm.lead.pls.update"
    _description = "Update the probabilities"

    def _default_pls_start_date(self):
        pls_start_date_config = (
            self.env["ir.config_parameter"].sudo().get_param("crm.pls_start_date")
        )
        return fields.Date.to_date(pls_start_date_config)

    def _default_pls_fields(self):
        pls_fields_config = (
            self.env["ir.config_parameter"].sudo().get_param("crm.pls_fields")
        )
        if pls_fields_config:
            names = pls_fields_config.split(",")
            fields = self.env["ir.model.fields"].search(
                [("name", "in", names), ("model", "=", "crm.lead")]
            )
            return self.env["crm.lead.scoring.frequency.field"].search(
                [("field_id", "in", fields.ids)]
            )
        else:
            return None

    pls_start_date = fields.Date(
        default=_default_pls_start_date,
        required=True,
    )
    pls_fields = fields.Many2many(
        comodel_name="crm.lead.scoring.frequency.field",
        default=_default_pls_fields,
    )

    def action_update_crm_lead_probabilities(self):
        if self.env.user._is_admin():
            set_param = self.env["ir.config_parameter"].sudo().set_param
            if self.pls_fields:
                pls_fields_str = ",".join(self.pls_fields.mapped("field_id.name"))
                set_param("crm.pls_fields", pls_fields_str)
            else:
                set_param("crm.pls_fields", "")
            set_param("crm.pls_start_date", str(self.pls_start_date))
            self.env["crm.lead"].sudo()._cron_update_automated_probabilities()
