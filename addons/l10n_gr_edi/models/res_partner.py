import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.sql import column_exists, create_column


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_gr_edi_branch_number = fields.Integer(
        string="Branch Number",
        help="Branch number in the Tax Registry",
        compute='_compute_l10n_gr_edi_branch_number',
        store=True,
        readonly=False,
    )
    l10n_gr_edi_contracting_authority_name = fields.Char(
        string="Contracting authority",
        help="Description-name of the procurement dept.(e.g. Ministry of Justice)"
    )
    l10n_gr_edi_contracting_authority_code = fields.Char(
        string="Contracting authority code",
        help="Code of the contracting authority (e.g. 2048.8010430600.00061)"
    )
    invoice_edi_format = fields.Selection(selection_add=[('ubl_gr', "Greece (Greek CIUS BIS 3.0)")])

    def _auto_init(self):
        if not column_exists(self.env.cr, 'res_partner', 'l10n_gr_edi_branch_number'):
            create_column(self.env.cr, 'res_partner', 'l10n_gr_edi_branch_number', 'int4')
        return super()._auto_init()

    @api.depends('country_code')
    def _compute_l10n_gr_edi_branch_number(self):
        for partner in self:
            if partner.country_code == 'GR':
                partner.l10n_gr_edi_branch_number = partner.l10n_gr_edi_branch_number or 0
            else:
                partner.l10n_gr_edi_branch_number = False

    @api.constrains('l10n_gr_edi_contracting_authority_code')
    def _check_l10n_gr_edi_contracting_authority_format(self):
        for partner in self:
            if partner.country_id.code == 'GR' and partner.l10n_gr_edi_contracting_authority_code:
                if not re.match(r'^\d+\.\d+\.\d+$', partner.l10n_gr_edi_contracting_authority_code):
                    raise ValidationError(self.env._("Greek contracting authority code is in invalid format"))

    def _get_edi_builder(self, invoice_edi_format):
        if invoice_edi_format == 'ubl_gr':
            return self.env['account.edi.xml.ubl_gr']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['ubl_gr'] = {'countries': ['GR'], 'on_peppol': True}
        return formats_info
