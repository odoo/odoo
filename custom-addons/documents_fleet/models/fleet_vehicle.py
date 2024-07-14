# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class FleetVehicle(models.Model):
    _name = 'fleet.vehicle'
    _inherit = ['fleet.vehicle', 'documents.mixin']

    documents_fleet_settings = fields.Boolean(related="company_id.documents_fleet_settings", string="Centralize Fleet Documents")
    document_count = fields.Integer(compute='_compute_document_count', string='Documents')

    def _compute_document_count(self):
        document_data = self.env['documents.document']._read_group([
            ('res_id', 'in', self.ids), ('res_model', '=', self._name)],
            groupby=['res_id'], aggregates=['__count'])
        mapped_data = dict(document_data)
        for record in self:
            record.document_count = mapped_data.get(record.id, 0)

    def _get_document_folder(self):
        return self.company_id.documents_fleet_folder

    def _get_document_owner(self):
        return self.env.user

    def _get_document_tags(self):
        return self.company_id.documents_fleet_tags

    def _check_create_documents(self):
        return self.company_id.documents_fleet_settings and super()._check_create_documents()

    def action_open_attachments(self):
        self.ensure_one()
        if not self.company_id.documents_fleet_settings:
            return True
        fleet_folder = self._get_document_folder()
        fleet_tags = self._get_document_tags()
        action = self.env['ir.actions.act_window']._for_xml_id('documents.document_action')
        action['domain'] = [('res_model', '=', self._name), ('res_id', '=', self.id),]
        action['context'] = {
            'default_res_id': self.id,
            'default_res_model': self._name,
            'searchpanel_default_folder_id': fleet_folder.id,
            'searchpanel_default_tag_ids': fleet_tags.ids,
        }
        return action
