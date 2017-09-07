# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    resource_calendar_ids = fields.One2many(
        'resource.calendar', 'company_id', 'Working Hours')
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Default Working Hours', ondelete='restrict')

    @api.model
    def _init_data_resource_calendar(self):
        for company in self.search([('resource_calendar_id', '=', False)]):
            company.resource_calendar_id = self.env['resource.calendar'].create({'name': _('Standard 40 hours/week')}).id

    @api.model
    def create(self, values):
        if not values.get('resource_calendar_id'):
            values['resource_calendar_id'] = self.env['resource.calendar'].sudo().create({'name': _('Standard 40 hours/week')}).id
        company = super(ResCompany, self).create(values)
        # calendar created from form view: no company_id set because record was still not created
        if not company.resource_calendar_id.company_id:
            company.resource_calendar_id.company_id = company.id
        return company
