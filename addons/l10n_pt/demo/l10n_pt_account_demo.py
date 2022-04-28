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
        for i, nb_lines in enumerate([5, 10, 15, 20, 25, 30, 40]):
            invoice_line_ids = []
            for _ in range(nb_lines):
                invoice_line_ids.append(
                    Command.create({
                        'product_id': ref(f'product.consu_delivery_0{randint(1, 4)}').id,
                        'quantity': randint(1, 10)
                    })
                )
            moves[f'{cid}_demo_invoice_{nb_moves+i+1}'] = {
                'move_type': 'out_invoice',
                'partner_id': ref('base.res_partner_12').id,
                'invoice_user_id': ref('base.user_demo').id,
                'invoice_date': time.strftime('%Y-%m-%d'),
                'invoice_line_ids': invoice_line_ids
            }
        return 'account.move', moves
