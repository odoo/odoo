# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

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
        ], string="GST Treatment")
    l10n_in_country_code = fields.Char(related='country_id.code', string='Country code')
    l10n_in_journal_count = fields.Integer(compute='_compute_l10n_in_journal_count', string='Journals')

    def _compute_l10n_in_journal_count(self):
        for unit in self:
            count = self.env['account.journal'].search_count([('l10n_in_gstin_partner_id','=',unit.id)])
            unit.l10n_in_journal_count = count

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
        return res + ['l10n_in_gst_treatment']

    def _l10n_in_check_gstn_unit(self):
        self.ensure_one()
        if not self.vat:
            raise ValidationError(_('The GST Number is required to setup the unit %s') % (self.name))
        if not self.state_id:
            raise ValidationError(_('The State is required to setup the unit %s') % (self.name))
        if self.state_id and self.state_id.l10n_in_tin != self.vat[0:2]:
            raise ValidationError(_('The GST Number %s is not valid for the state %s.') % (self.vat, self.state_id.name))

    def write(self, vals):
        result = super().write(vals)
        if self._context.get('l10n_in_multiple_gstn', False):
            for gstn in self:
                gstn._l10n_in_check_gstn_unit()
        return result

    def _l10n_in_rearrange_journal_groups(self):
        AccountJournal = self.env['account.journal']
        AccountJournalGroup = self.env['account.journal.group']
        gstn_units = self.env['res.partner'].search(['|', ('parent_id','=', self.env.company.partner_id.id),
            ('id','=', self.env.company.partner_id.id)])

        for gstn in gstn_units:
            journal_group = AccountJournalGroup.search([('name','ilike',gstn.vat)], limit=1)
            journal_ids = AccountJournal.search([('company_id','=',self.env.company.id),
                ('type','in',['sale', 'purchase']), ('l10n_in_gstin_partner_id', '!=', gstn.id)])

            if not journal_group:
                journal_group = AccountJournalGroup.create({
                    'name': '%s (%s)' % (gstn.display_name, gstn.vat)
                })
            journal_group.excluded_journal_ids = journal_ids

    def _l10n_in_setup_gstn(self):
        self.ensure_one()
        AccountJournal = self.env['account.journal']
        state_code = self.state_id.code

        journals = [
            {'name': _('Tax Invoices'), 'type': 'sale', 'code': _('INV'), 'favorite': True, 'sequence': 5},
            {'name': _('Vendor Bills'), 'type': 'purchase', 'code': _('BILL'), 'favorite': True, 'sequence': 7}
        ]

        for journal in journals:
            vals = {
                'l10n_in_gstin_partner_id': self.id,
                'type': journal['type'],
                'name': '%s (%s)' % (journal['name'], state_code),
                'code': journal['code'],
                'company_id': self.env.company.id,
                'show_on_dashboard': journal['favorite'],
                'color': journal.get('color', False),
                'sequence': journal['sequence'],
                'active': True
            }
            AccountJournal.create(vals)

    @api.model
    def create(self, vals):
        if self._context.get('l10n_in_multiple_gstn', False):
            vals.update({
                'parent_id': self.env.company.partner_id.id,
                'type': 'other',
                'l10n_in_shipping_gstin': vals.get('vat')
            })
        res = super(ResPartner, self).create(vals)
        if self._context.get('l10n_in_multiple_gstn', False):
            res._l10n_in_check_gstn_unit()
            res._l10n_in_setup_gstn()
            res._l10n_in_rearrange_journal_groups()
        return res
