import typing

from odoo import fields, models

if typing.TYPE_CHECKING:
    from .res_partner_bank import ResPartnerBank


class ResPartner(models.Model):
    _inherit = 'res.partner'

    bank_ids: ResPartnerBank = fields.One2many('res.partner.bank', 'partner_id', string='Banks')

    def write(self, vals):
        super().write(vals)

        if vals.get('name'):
            for partner in self:
                for bank in partner.bank_ids:
                    if bank.holder_name == partner.name:
                        bank.holder_name = vals['name']
