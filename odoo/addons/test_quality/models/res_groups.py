# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import collections

from odoo import api, fields, models, _

class ResGroups(models.Model):
    _inherit = 'res.groups'

    xml_id = fields.Char(string="External ID", compute='_compute_xml_id',
                         help="ID of the group defined in xml file")

    def _compute_xml_id(self):
        xml_ids = collections.defaultdict(list)
        domain = [('model', '=', 'res.groups'), ('res_id', 'in', self.ids)]
        for data in self.env['ir.model.data'].sudo().search_read(domain, ['module', 'name', 'res_id']):
            xml_ids[data['res_id']].append("%s.%s" % (data['module'], data['name']))
        for group in self:
            group.xml_id = xml_ids.get(group.id, [''])[0]

    transitive_access_ids = fields.Many2many("ir.model.access", string="Inherited Access Rights", compute="_compute_transitive_rules")
    transitive_rule_ids = fields.Many2many("ir.rule", string="Inherited Record Rules", compute="_compute_transitive_rules")

    @api.depends("trans_implied_ids.model_access", "trans_implied_ids.rule_groups")
    def _compute_transitive_access_ids(self):
        for group in self:
            group.transitive_access_ids = group.trans_implied_ids.model_access
            group.transitive_rule_ids = group.trans_implied_ids.rule_groups