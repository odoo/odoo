# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    profo_sequence_id = fields.Many2one('ir.sequence', string='Pro Forma Order IDs Sequence', readonly=True,
                                        help="This sequence is automatically created by Odoo but you can change it "
                                             "to customize the reference numbers of your pro forma orders.", copy=False,
                                        ondelete='restrict')
    profo_sequence_line_id = fields.Many2one('ir.sequence', string='Pro Forma Order Line IDs Sequence', readonly=True,
                                       help="This sequence is automatically created by Odoo but you can change it "
                                            "to customize the reference numbers of your orders lines.", copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            IrSequence = self.env['ir.sequence'].sudo()
            val = {
                'name': _('POS Profo Order %s', vals['name']),
                'padding': 4,
                'prefix': "Profo %s/" % vals['name'],
                'code': "pos.order_pro_forma",
                'company_id': vals.get('company_id', False),
            }
            # force sequence_id field to new pos.order sequence
            vals['profo_sequence_id'] = IrSequence.create(val).id

            val.update(name=_('POS order line %s', vals['name']), code='pos.order_line_pro_forma')
            vals['profo_sequence_line_id'] = IrSequence.create(val).id

        pos_configs = super().create(vals_list)
        return pos_configs
