# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_it_origin_document_type = fields.Selection(
        string="Origin Document Type",
        selection=[('purchase_order', 'Purchase Order'), ('contract', 'Contract'), ('agreement', 'Agreement')],
        readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    l10n_it_origin_document_name = fields.Char(
        string="Origin Document Name",
        readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    l10n_it_origin_document_date = fields.Date(
        string="Origin Document Date",
        readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    l10n_it_cig = fields.Char(
        string="CIG",
        readonly=True, states={'draft': [('readonly', False)]}, copy=False,
        help="Tender Unique Identifier")
    l10n_it_cup = fields.Char(
        string="CUP",
        readonly=True, states={'draft': [('readonly', False)]}, copy=False,
        help="Public Investment Unique Identifier")
    # Technical field for showing the above fields or not
    l10n_it_partner_pa = fields.Boolean(compute='_compute_l10n_it_partner_pa')

    @api.depends('commercial_partner_id.l10n_it_pa_index', 'company_id')
    def _compute_l10n_it_partner_pa(self):
        for move in self:
            move.l10n_it_partner_pa = (move.country_code == 'IT' and move.commercial_partner_id.l10n_it_pa_index and
                                       len(move.commercial_partner_id.l10n_it_pa_index) == 6)

    def _prepare_fatturapa_export_values(self):
        """Add origin document features."""
        template_values = super()._prepare_fatturapa_export_values()
        template_values.update({
            'origin_document_type': self.l10n_it_origin_document_type,
            'origin_document_name': self.l10n_it_origin_document_name,
            'origin_document_date': self.l10n_it_origin_document_date,
            'cig': self.l10n_it_cig,
            'cup': self.l10n_it_cup,
        })
        return template_values
