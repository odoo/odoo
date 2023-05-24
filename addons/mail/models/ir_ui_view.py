# -*- coding: utf-8 -*-
from odoo import fields, models, api


class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('activity', 'Activity')])

    def _postprocess_tag_field(self, node, name_manager, node_info):
        if node.xpath("ancestor::div[hasclass('oe_chatter')]"):
            # Pass the postprocessing of the mail thread fields
            # The web client makes it completely custom, and this is therefore pointless.
            name_manager.has_field(node, node.get('name'), {})
            return
        return super()._postprocess_tag_field(node, name_manager, node_info)

    def _is_qweb_based_view(self, view_type):
        return view_type == "activity" or super()._is_qweb_based_view(view_type)

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('inherit_id'):
                self.prompt_client_refresh(self.env['ir.ui.view'].sudo().browse(values['inherit_id']))
        return super(View, self).create(vals_list)

    def unlink(self):
        self.prompt_client_refresh(self)
        return super(View, self).unlink()

    def write(self, vals):
        self.prompt_client_refresh(self)
        return super(View, self).write(vals)

    def prompt_client_refresh(self, parent_view=False):
        models = [view.model for view in parent_view if view.type == 'form']
        if len(models) > 0:
            self.env['bus.bus']._sendone('broadcast', 'client_refresh', {
                'models': models,
            })
