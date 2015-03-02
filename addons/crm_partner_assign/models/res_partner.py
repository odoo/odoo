# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class ResPartnerGrade(models.Model):
    _order = 'sequence'
    _name = 'res.partner.grade'

    sequence = fields.Integer()
    active = fields.Boolean(default=True)
    name = fields.Char(string='Grade Name')
    partner_weight = fields.Integer(string='Grade Weight',
                                    default=1,
                                    help="Gives the probability to assign a lead to this partner. (0 means no assignation.)")


class ResPartnerActivation(models.Model):
    _name = 'res.partner.activation'
    _order = 'sequence'

    sequence = fields.Integer()
    name = fields.Char(required=True)


class ResPartner(models.Model):
    _inherit = "res.partner"

    partner_weight = fields.Integer(string='Grade Weight',
        help="Gives the probability to assign a lead to this partner. (0 means no assignation.)")
    grade_id = fields.Many2one('res.partner.grade', string='Grade')
    activation = fields.Many2one('res.partner.activation', index=True)
    date_partnership = fields.Date(string='Partnership Date')
    date_review = fields.Date(string='Latest Partner Review')
    date_review_next = fields.Date(string='Next Partner Review')
    # customer implementation
    assigned_partner_id = fields.Many2one('res.partner', string='Implemented by')
    implemented_partner_ids = fields.One2many('res.partner', 'assigned_partner_id',
                                              string='Implementation References')

    @api.onchange('grade_id')
    def onchange_grade_id(self):
        self.partner_weight = self.grade_id.partner_weight

    def search_geo_localize_partner(self, latitude, longitude, country):
        # 1. first way: in the same country, small area
        Partners = self.search([
            ('partner_weight', '>', 0),
            ('partner_latitude', '>', latitude - 2),
            ('partner_latitude', '<', latitude + 2),
            ('partner_longitude', '>', longitude - 1.5),
            ('partner_longitude', '<', longitude + 1.5),
            ('country_id', '=', country.id),
        ])

        # 2. second way: in the same country, big area
        if not Partners:
            Partners = self.search([
                ('partner_weight', '>', 0),
                ('partner_latitude', '>', latitude - 4),
                ('partner_latitude', '<', latitude + 4),
                ('partner_longitude', '>', longitude - 3),
                ('partner_longitude', '<', longitude + 3),
                ('country_id', '=', country.id),
            ])

        # 3. third way: in the same country, extra large area
        if not Partners:
            Partners = self.search([
                ('partner_weight', '>', 0),
                ('partner_latitude', '>', latitude - 8),
                ('partner_latitude', '<', latitude + 8),
                ('partner_longitude', '>', longitude - 8),
                ('partner_longitude', '<', longitude + 8),
                ('country_id', '=', country.id),
            ])

        # 5. fifth way: anywhere in same country
        if not Partners:
            # still haven't found any, let's take all partners in the
            # country!
            Partners = self.search([
                ('partner_weight', '>', 0),
                ('country_id', '=', country.id),
            ])

        # 6. sixth way: closest partner whatsoever, just to have at
        # least one result
        if not Partners:
            # warning: point() type takes (longitude, latitude) as
            # parameters in this order!
            self.env.cr.execute("""SELECT id, distance
                          FROM  (select id, (point(partner_longitude, partner_latitude) <-> point(%s,%s)) AS distance FROM res_partner
                          WHERE partner_longitude is not null
                                AND partner_latitude is not null
                                AND partner_weight > 0) AS d
                          ORDER BY distance LIMIT 1""", (longitude, latitude))
            res = self.env.cr.dictfetchone()
            if res:
                Partners = Partners + self.browse(res['id'])
        return Partners
