import base64

from cryptography.hazmat.primitives import serialization

from odoo import fields, models
from odoo.tools import SQL


class RentalProperty(models.Model):
    _name = 'rental.property'
    _description = "Rental Property"
    _order = 'name'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    owner_id = fields.Many2one('res.partner', string="Owner", required=True)
    owner_bank_account = fields.Char("Owner IBAN")
    rent_amount = fields.Float()
    lease_ids = fields.One2many('rental.lease', 'property_id')
    active_lease_count = fields.Integer(compute='_compute_active_lease_count')

    # Credentials of the listing website the properties are published on.
    listing_api_token = fields.Char("Listing API Token")
    listing_signing_key = fields.Binary("Listing Signing Key", groups='base.group_system')

    def _compute_active_lease_count(self):
        query = self.env['rental.lease']._search([('property_id', 'in', self.ids), ('state', '=', 'active')])
        rows = self.env.execute_query(SQL("%s GROUP BY property_id", query.select(SQL("property_id"), SQL("COUNT(*)"))))
        counts = dict(rows)
        for prop in self:
            prop.active_lease_count = counts.get(prop.id, 0)

    def get_listing_signing_key(self):
        self.ensure_one()
        return serialization.load_pem_private_key(
            base64.b64decode(self.sudo().listing_signing_key),
            password=None,
        )

    def occupancy_report(self, order_by='name'):
        self.env.cr.execute(f"""
            SELECT p.name, COUNT(l.id) AS leases, SUM(l.rent_amount) AS income
              FROM rental_property p
         LEFT JOIN rental_lease l ON l.property_id = p.id
          GROUP BY p.name
          ORDER BY {order_by}
        """)
        return self.env.cr.dictfetchall()
