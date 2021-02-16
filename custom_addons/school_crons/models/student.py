# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_student = fields.Boolean(string='Is Student', default=False)
    is_faculty = fields.Boolean(string='Is faculty', default=False)

    @api.model
    def create(self, vals_list):
        if vals_list.get('is_student'):
            super(ResPartner, self).create(vals_list)
            user = self.env['res.users'].create({
                'name': vals_list['name'],
                'login': vals_list['email'],
                'password': 2012,
                'partner_id': self.env['res.partner'].search([('is_student', '=', True)]).ids[-1],
                'company_id': self.env['res.company'].search([]).ids[-1],
                'company_ids': [(4, self.env['res.company'].search([]).ids[-1], 0)],
                'sel_groups_1_9_10': 1,
                'sel_groups_38_39': 38,
            })
            return user
        elif vals_list.get('is_faculty'):
            super(ResPartner, self).create(vals_list)
            user = self.env['res.users'].create({
                'name':vals_list['name'],
                'login': vals_list['email'],
                'password': 2012,
                'partner_id': self.env['res.partner'].search([]).ids[-1],
                'company_id': self.env['res.company'].search([]).ids[-1],
                'company_ids': [(4, self.env['res.company'].search([]).ids[-1], 0)],
                'sel_groups_1_9_10': 1,
                'sel_groups_38_39': 39,
            })
            return user
        return super(ResPartner, self).create(vals_list)
