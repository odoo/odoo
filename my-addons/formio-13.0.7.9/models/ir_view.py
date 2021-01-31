# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

from odoo import fields, models


FORMIO_VIEW_TYPES = [
    ('formio_builder', 'Form.io Builder'),
    ('formio_form', 'Form.io Form')
]


class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=FORMIO_VIEW_TYPES)


class IrActionsActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=FORMIO_VIEW_TYPES)
