# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import collections

from odoo import api, fields, models, _

class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    csv_id = fields.Char(string="External ID", compute='_compute_csv_id',
                         help="ID of the access defined in csv file")

    def _compute_csv_id(self):
        csv_ids = collections.defaultdict(list)
        domain = [('model', '=', 'ir.model.access'), ('res_id', 'in', self.ids)]
        for data in self.env['ir.model.data'].sudo().search_read(domain, ['module', 'name', 'res_id']):
            csv_ids[data['res_id']].append("%s.%s" % (data['module'], data['name']))
        for access in self:
            access.csv_id = csv_ids.get(access.id, [''])[0]

    def _is_loaded_after(self, rule):
        """Check if self is loaded after rule because of modules deps"""
        if self.csv_id and rule.csv_id:
            mod_1_name = self.csv_id.split(".")[0]
            mod_2_name = rule.csv_id.split(".")[0]
            if mod_1_name == mod_2_name:
                # Same module, loaded together.
                return True
            module_1 = self.env['ir.module.module'].search([('name', '=', mod_1_name)])
            module_2 = self.env['ir.module.module'].search([('name', '=', mod_2_name)])
            if module_2 in module_1.required_module_ids:
                return True
        return False
