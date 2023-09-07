# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_it_origin_document_type = fields.Selection(
        string="Origin Document Type",
        selection=[('purchase_order', 'Purchase Order'), ('contract', 'Contract'), ('agreement', 'Agreement')],
        copy=False)
    l10n_it_origin_document_name = fields.Char(
        string="Origin Document Name",
        copy=False)
    l10n_it_origin_document_date = fields.Date(
        string="Origin Document Date",
        copy=False)
    l10n_it_cig = fields.Char(
        string="CIG",
        copy=False,
        help="Tender Unique Identifier")
    l10n_it_cup = fields.Char(
        string="CUP",
        copy=False,
        help="Public Investment Unique Identifier")
    # Technical field for showing the above fields or not
    l10n_it_partner_pa = fields.Boolean(compute='_compute_l10n_it_partner_pa')

    @api.depends('commercial_partner_id.l10n_it_pa_index', 'company_id')
    def _compute_l10n_it_partner_pa(self):
        for move in self:
            move.l10n_it_partner_pa = (move.country_code == 'IT' and move.commercial_partner_id.l10n_it_pa_index and
                                       len(move.commercial_partner_id.l10n_it_pa_index) == 6)

    def _l10n_it_edi_get_values(self, pdf_values=None):
        """Add origin document features."""
        template_values = super()._l10n_it_edi_get_values(pdf_values=pdf_values)
        template_values.update({
            'origin_document_type': self.l10n_it_origin_document_type,
            'origin_document_name': self.l10n_it_origin_document_name,
            'origin_document_date': self.l10n_it_origin_document_date,
            'cig': self.l10n_it_cig,
            'cup': self.l10n_it_cup,
        })
        return template_values

    def _l10n_it_edi_base_export_data_check(self):
        errors = super()._l10n_it_edi_base_export_data_check()
        if self.l10n_it_partner_pa:
            if not self.l10n_it_origin_document_type:
                errors.append(_("This invoice targets the Public Administration, please fill out"
                                " Origin Document Type field in the Electronic Invoicing tab."))
            if self.l10n_it_origin_document_date and self.l10n_it_origin_document_date > fields.Date.today():
                errors.append(_("The Origin Document Date cannot be in the future."))
        return errors
