import typing

from odoo import fields, models

if typing.TYPE_CHECKING:
    from .res_partner_bank import ResPartnerBank


class ResCompany(models.CachedModel):
    _inherit = 'res.company'

    bank_ids: ResPartnerBank = fields.One2many(related='partner_id.bank_ids', readonly=False)
