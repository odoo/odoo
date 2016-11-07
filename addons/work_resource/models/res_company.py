# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = ['res.company']

    def _get_default_resource_calendar_ids(self):
        return [(0, 0, {'name': 'Standard 40 hours/week'})]

    resource_calendar_ids = fields.One2many(
        'work.calendar', 'company_id', 'Working Hours',
        default=_get_default_resource_calendar_ids)
    resource_calendar_id = fields.Many2one(
        'work.calendar', 'Default Working Hours')

    @api.onchange('resource_calendar_ids')
    def _onchange_resource_calendar_ids(self):
        if not self.resource_calendar_id and self.resource_calendar_ids:
            self.resource_calendar_id = self.resource_calendar_ids[0].id

    def init(self):
        """ Update existing companies by setting their default work calendar
        to the first one that is linked to them. This is necessary to make
        calendar work out of the box. """
        query = 'SELECT id FROM "%s" WHERE "resource_calendar_id" is NULL' % (
            self._table)
        self.env.cr.execute(query)
        company_ids = self.env.cr.fetchall()
        for company_id in company_ids:
            query = 'SELECT id FROM "work_calendar" WHERE "company_id" = %s' % (
                company_id[0])
            self.env.cr.execute(query)
            calendar_ids = self.env.cr.fetchall()
            if calendar_ids:
                query = 'UPDATE "%s" SET "resource_calendar_id"=%%s WHERE id = %s' % (
                    self._table, company_id[0])
                self.env.cr.execute(query, (calendar_ids[0][0],))
        return super(ResCompany, self).init()

    @api.model
    def create(self, values):
        company = super(ResCompany, self).create(values)
        if company.resource_calendar_ids and not company.resource_calendar_id:
            company.write({'resource_calendar_id': company.resource_calendar_ids[0].id})
        return company
