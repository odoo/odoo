from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_gr_edi_branch_number = fields.Integer(
        string="Branch Number",
        help="Branch number in the Tax Registry",
        compute='_compute_l10n_gr_edi_branch_number',
        store=True,
        readonly=False,
    )

    def _get_fields_to_skip_compute_on_init(self):
        fields_to_skip_compute = super()._get_fields_to_skip_compute_on_init()
        fields_to_skip_compute.update([
            'l10n_gr_edi_branch_number',
        ])
        return fields_to_skip_compute

    @api.depends('country_code')
    def _compute_l10n_gr_edi_branch_number(self):
        for partner in self:
            if partner.country_code == 'GR':
                partner.l10n_gr_edi_branch_number = partner.l10n_gr_edi_branch_number or 0
            else:
                partner.l10n_gr_edi_branch_number = False
