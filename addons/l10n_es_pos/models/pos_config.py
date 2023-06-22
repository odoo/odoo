from odoo import _, api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    is_spanish = fields.Boolean(string="Company located in Spain", compute="_is_company_spanish")

    def _is_company_spanish(self):
        for pos in self:
            pos.is_spanish = pos.company_id.country_id.code == "ES"

    l10n_es_simplified_invoice_limit = fields.Float(
        string="Sim.Inv limit amount",
        digits="Account",
        help="Over this amount is not legally possible to create a simplified invoice",
        default=400,
    )
    l10n_es_simplified_invoice_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Simplified Invoice IDs Sequence",
        help="Autogenerate for each POS created",
        copy=False,
        readonly=True,
    )

    def get_l10n_es_simplified_invoice_number(self):
        self.ensure_one()
        return (
            self.l10n_es_simplified_invoice_sequence_id._get_current_sequence().number_next_actual
        )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._set_simplified_l10n_es_sequence()
        return records

    @api.model
    def _set_simplified_l10n_es_sequence(self):
        for record in self:
            if record.is_spanish and not record.l10n_es_simplified_invoice_sequence_id:
                sequence = self.env["ir.sequence"].create(
                    {
                        "name": _("Simplified Invoice %s") % record.name,
                        "implementation": "standard",
                        "padding": record._get_default_padding(),
                        "prefix": record.env["ir.sequence"]._sanitize_prefix(
                            f"{record.name}{record._get_default_prefix()}"
                        ),
                        "code": "pos.config.simplified_invoice",
                        "company_id": record.company_id.id,
                    }
                )
                record.l10n_es_simplified_invoice_sequence_id = sequence.id

    def write(self, vals):
        if not self._context.get("copy_pos_config") and "name" not in vals:
            for pos in self:
                sequence = pos.l10n_es_simplified_invoice_sequence_id
                sequence.check_simplified_invoice_unique_prefix()
        if "name" in vals:
            prefix = self.l10n_es_simplified_invoice_prefix.replace(self.name, vals["name"])
            if prefix != self.l10n_es_simplified_invoice_prefix:
                self.l10n_es_simplified_invoice_sequence_id.update(
                    {
                        "prefix": prefix,
                        "name": (
                            self.l10n_es_simplified_invoice_sequence_id.name.replace(
                                self.name, vals["name"]
                            )
                        ),
                    }
                )
        return super().write(vals)

    def unlink(self):
        self.mapped("l10n_es_simplified_invoice_sequence_id").unlink()
        return super().unlink()

    def _get_default_padding(self):
        return self.env["ir.config_parameter"].get_param(
            "l10n_es_pos.simplified_invoice_sequence.padding", 4
        )

    def _get_default_prefix(self):
        return self.env["ir.config_parameter"].get_param(
            "l10n_es_pos.simplified_invoice_sequence.prefix", "-"
        )
