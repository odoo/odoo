# -*- coding: utf-8 -*-
from openerp import api, models

class PrintOrderlineWizard(models.TransientModel):

    _inherit = 'print.order.line.wizard'

    @api.model
    def _default_selection_state(self):
        selection = super(PrintOrderlineWizard, self)._default_selection_state()
        selection.append(('sale_order_wrong_state', 'Wrong Sale Order State'))
        return selection

    @api.one
    def _compute_state(self):
        super(PrintOrderlineWizard, self)._compute_state()
        state = self.state
        if self.res_model == 'sale.order':
            if not self.env['sale.order'].browse(self.res_id).state in ['draft', 'sent', 'progress', 'manual']:
                state = 'sale_order_wrong_state'
        self.state = state
