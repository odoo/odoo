from odoo import fields, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    l10n_eg_pos_eta_code = fields.Selection([('C', 'Cash'),
                                             ('V', 'Visa'),
                                             ('P', 'Points'),
                                             ('CC', 'Cash with contractor'),
                                             ('VC', 'Visa with contractor'),
                                             ('VO', 'Vouchers'),
                                             ('PR', 'Promotion'),
                                             ('GC', 'Gift Card'),
                                             ('O', 'Others')
                                             ], default="C", required=True, string='ETA Code')
