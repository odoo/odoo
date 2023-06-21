# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

TEST_GST_NUMBER = "36AABCT1332L011"

class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_in_gst_treatment = fields.Selection([
            ('regular', 'Registered Business - Regular'),
            ('composition', 'Registered Business - Composition'),
            ('unregistered', 'Unregistered Business'),
            ('consumer', 'Consumer'),
            ('overseas', 'Overseas'),
            ('special_economic_zone', 'Special Economic Zone'),
            ('deemed_export', 'Deemed Export'),
            ('uin_holders', 'UIN Holders'),
        ], string="GST Treatment")

    l10n_in_pan = fields.Char(
        string="PAN",
        help="PAN enables the department to link all transactions of the person with the department.\n"
             "These transactions include taxpayments, TDS/TCS credits, returns of income/wealth/gift/FBT,"
             " specified transactions, correspondence, and so on.\n"
             "Thus, PAN acts as an identifier for the person with the tax department."
    )

    @api.onchange('company_type')
    def onchange_company_type(self):
        res = super().onchange_company_type()
        if self.country_id and self.country_id.code == 'IN':
            self.l10n_in_gst_treatment = (self.company_type == 'company') and 'regular' or 'consumer'
        return res

    @api.onchange('country_id')
    def _onchange_country_id(self):
        res = super()._onchange_country_id()
        if self.country_id and self.country_id.code != 'IN':
            self.l10n_in_gst_treatment = 'overseas'
        elif self.country_id and self.country_id.code == 'IN':
            self.l10n_in_gst_treatment = (self.company_type == 'company') and 'regular' or 'consumer'
        return res

    @api.onchange('vat')
    def onchange_vat(self):
        if self.vat and self.check_vat_in(self.vat):
            state_id = self.env['res.country.state'].search([('l10n_in_tin', '=', self.vat[:2])], limit=1)
            if state_id:
                self.state_id = state_id

    @api.model
    def _commercial_fields(self):
        res = super()._commercial_fields()
        return res + ['l10n_in_gst_treatment', 'l10n_in_pan']

    def check_vat_in(self, vat):
        """
            This TEST_GST_NUMBER is used as test credentials for EDI
            but this is not a valid number as per the regular expression
            so TEST_GST_NUMBER is considered always valid
        """
        if vat == TEST_GST_NUMBER:
            return True
        return super().check_vat_in(vat)

    def update_draft_invoices(self):
        draft_move_ids = self.env['account.move'].search([
            ('state', '=', 'draft'),
            ('partner_id', '=', self.id),
            ('company_id', '=', self.env.company.id),
            ('move_type', '!=', 'entry')
        ])
        draft_move_ids.write({'l10n_in_gst_treatment': self.l10n_in_gst_treatment})
        draft_move_count_by_type_name = {}
        for move in draft_move_ids:
            type_name = move.type_name
            draft_move_count_by_type_name.setdefault(type_name, 0)
            draft_move_count_by_type_name[type_name] += 1
        action = self.env.ref('l10n_in.action_view_move')
        action.domain = [('id', 'in', draft_move_ids.ids)]
        message = (", ".join(_("%s %s", moves, type_name) for type_name, moves in draft_move_count_by_type_name.items()))
        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': (_('The following Invoice/Bills is updated')),
                'message': message + ' %s',
                'links': [{
                    'label': 'View moves',
                    'url': f'#action={action.id}&model=account.move&view_type=list'
                }],
                'sticky': False,
            }
        }
        return notification
