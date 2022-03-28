# -*- coding: utf-8 -*-
from odoo import models


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    def _postprocess_prepare_2many_inline_view_widgets(self):
        widgets = super()._postprocess_prepare_2many_inline_view_widgets()
        widgets.extend(['one2many', 'many2many'])
        return widgets
