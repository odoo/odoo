from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_gr_edi_branch_number = fields.Integer(
        string="MyDATA Branch Number",
        help="Branch number in the Tax Registry",
        compute='_compute_l10n_gr_edi_branch_number',
        store=True,
        readonly=False,
    )

    @api.depends('country_code')
    def _compute_l10n_gr_edi_branch_number(self):
        for partner in self:
            if partner.country_code == 'GR':
                partner.l10n_gr_edi_branch_number = partner.l10n_gr_edi_branch_number or 0
            else:
                partner.l10n_gr_edi_branch_number = False
