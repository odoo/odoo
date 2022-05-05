# -*- coding: utf-8 -*-
from odoo import api, models, Command
import time
from random import randint


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data_move(self):
        demo_data_move = super()._get_demo_data_move()
        if self.env.company.country_id.code != 'PT':
            return demo_data_move
        cid = self.env.company.id
        ref = self.env.ref
        moves = demo_data_move[1]
        # Create new invoices with loooots of lines to test the multi-page carry-over
        nb_moves = len(moves)
        for currency_id in (1, 2, 3):
            self.env["res.currency"].browse(currency_id).active = True
        for i, nb_lines in enumerate([5, 10, 20, 30, 40, 60]):
            invoice_line_ids = []
            for _ in range(nb_lines):
                invoice_line_ids.append(
                    Command.create({
                        'product_id': ref(f'product.consu_delivery_0{randint(1, 3)}').id,
                        'quantity': randint(1, 10)
                    })
                )
            moves[f'{cid}_demo_invoice_{nb_moves+i+1}'] = {
                'move_type': 'out_invoice',
                'partner_id': ref('base.res_partner_12').id,
                'invoice_user_id': ref('base.user_demo').id,
                'invoice_date': time.strftime('%Y-%m-%d'),
                'invoice_line_ids': invoice_line_ids,
                'currency_id': randint(1, 3),
            }
        return 'account.move', moves
