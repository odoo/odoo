from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    bank_ids = fields.One2many('res.partner.bank', 'partner_id', string='Banks')

    def _write_setup(self, vals):
        vals = super()._write_setup(vals)

        if vals.get('name'):
            for partner in self:
                for bank in partner.bank_ids:
                    if bank.holder_name == partner.name:
                        bank.holder_name = vals['name']

        return vals
