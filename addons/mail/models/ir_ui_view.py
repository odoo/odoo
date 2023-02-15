# -*- coding: utf-8 -*-
from odoo import fields, models


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
