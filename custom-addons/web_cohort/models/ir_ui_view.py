# -*- coding: utf-8 -*-
from odoo import fields, models


class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('cohort', 'Cohort')])

    def _postprocess_tag_cohort(self, node, name_manager, node_info):
        for additional_field in ('date_start', 'date_stop'):
            if node.get(additional_field):
                name_manager.has_field(node, node.get(additional_field).split('.', 1)[0])
