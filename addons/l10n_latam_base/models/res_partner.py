from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_latam_identification_type_id = fields.Many2one(
        comodel_name="l10n_latam.identification.type",
        string="Identification Type",
        inverse="_inverse_vat",  # To trigger the vat checking
        default=lambda self: self.env.ref(
            "l10n_latam_base.it_vat", raise_if_not_found=False
        ),
        index="btree_not_null",
        bypass_search_access=True,
        help="The type of identification",
    )
    is_vat = fields.Boolean(related="l10n_latam_identification_type_id.is_vat")
    vat = fields.Char(
        string="Identification Number",
        help="Identification Number for selected type",
    )

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ["l10n_latam_identification_type_id"]

    def _run_check_identification(self, validation="error"):
        return

    def _check_vat(self, validation="error"):
        partners_vat = self.filtered(
            lambda p: (
                not p.l10n_latam_identification_type_id
                or p.l10n_latam_identification_type_id.is_vat
            )
        )
        super(ResPartner, partners_vat)._check_vat(validation=validation)
        (self - partners_vat)._run_check_identification(validation=validation)

    @api.onchange("vat", "country_id", "l10n_latam_identification_type_id")
    def _onchange_vat(self):
        super()._onchange_vat()

    def _get_fields_frontend_writable(self):
        frontend_writable_fields = super()._get_fields_frontend_writable()
        frontend_writable_fields.add("l10n_latam_identification_type_id")

        return frontend_writable_fields
