from odoo import fields, models


class IAPServicePack(models.Model):
    _name = 'iap.service.pack'
    _description = 'IAP Service Pack'

    name = fields.Char(required=True, readonly=True)
    display_name = fields.Char(compute='_compute_display_name')
    credit = fields.Float(required=True, readonly=True)
    price = fields.Float(string='Sales Price (EUR)', required=True, readonly=True)
    service_id = fields.Many2one('iap.service', required=True, readonly=True, index=True)
    iap_service_pack_identifier = fields.Integer(required=True, readonly=True)

    _unique_iap_service_pack_identifier = models.Constraint(
        'UNIQUE(iap_service_pack_identifier)',
        'Only one service pack can exist with a specific iap_service_pack_identifier',
    )

    def _compute_display_name(self):
        for pack in self:
            credit = round(pack.credit, None if pack.service_id.integer_balance else 4)
            pack.display_name = f"{pack.name} - {credit} {pack.service_id.unit_name} ({pack.price} EUR)"
