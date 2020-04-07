# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import collections

from odoo import api, fields, models, _

def value(rule):
    return sum(int(rule[perm]) for perm in ['perm_read', 'perm_write', 'perm_create', 'perm_unlink']) if rule else 0


class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    csv_id = fields.Char(string="External ID", compute='_compute_csv_id',
                         help="ID of the access defined in csv file")
    # VFE store True s.t. we can order by the csv_id the ir.model.access ?
    module_name = fields.Char(string="Loaded with module", compute="_compute_csv_id")
    data_name = fields.Char(compute="_compute_csv_id")

    def _compute_csv_id(self):
        csv_ids = collections.defaultdict(list)
        domain = [('model', '=', 'ir.model.access'), ('res_id', 'in', self.ids)]
        for data in self.env['ir.model.data'].sudo().search_read(domain, ['module', 'name', 'res_id']):
            csv_ids[data['res_id']].append("%s.%s" % (data['module'], data['name']))
        for access in self:
            access.csv_id = csv_ids.get(access.id, [''])[0]
            access.module_name, access.data_name = access.csv_id.split(".") if access.csv_id else ('','')

    def _is_loaded_after(self, rule):
        """Check if self is loaded after rule because of modules deps"""
        if not(self.csv_id and rule.csv_id):
            return False
        if self.module_name == rule.module_name:
            # Same module, loaded together.
            # Are targeted specifically early in the test.
            return False
        module = self.env['ir.module.module'].search([('name', '=', self.module_name)])
        if rule.module_name in module.required_module_ids.mapped("name"):
            return True
        return False

    def _is_loaded_with(self, rule):
        return self.module_name == rule.module_name

    def _is_implied_by(self, rules):
        for rule in rules:
            if value(self) <= value(rule):
                if self._is_loaded_with(rule):
                    if rule.group_id == self.group_id:
                        # Two rules targeting same (model,group) are managed later
                        # return False here
                        return False
                    else:
                        return rule
                elif self._is_loaded_after(rule):
                    return rule
        return False
