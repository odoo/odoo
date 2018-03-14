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
        self.search([('resource_calendar_id', '=', False)])._create_resource_calendar()

    def _create_resource_calendar(self):
        for company in self:
            company.resource_calendar_id = self.env['resource.calendar'].create({
                'name': _('Standard 40 hours/week'),
                'company_id': company.id
            }).id

    @api.model
    def create(self, values):
        company = super(ResCompany, self).create(values)
        if not company.resource_calendar_id:
            company.sudo()._create_resource_calendar()
        # calendar created from form view: no company_id set because record was still not created
        if not company.resource_calendar_id.company_id:
            company.resource_calendar_id.company_id = company.id
        return company
