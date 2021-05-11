# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

class FleetCategory(models.Model):
    _name = 'fleet.category'
    _description = 'Vehicle Fleet'

    def _get_default_favorite_user_ids(self):
        return [(6, 0, [self.env.uid])]

    name = fields.Char()
    active = fields.Boolean(default=True)
    tag_ids = fields.Many2many('fleet.category.tag', string='Tags')
    description = fields.Text()
    manager_id = fields.Many2one(
        'res.users', string='Fleet Manager',
        default=lambda self: self.env.user,
        domain=lambda self: [('groups_id', 'in', self.env.ref('fleet.fleet_group_manager').id)],
    )

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
    )
    color = fields.Integer()

    vehicle_ids = fields.One2many('fleet.vehicle', 'fleet_id', string='Vehicles')
    car_count = fields.Integer(compute='_compute_vehicle_counts')
    bike_count = fields.Integer(compute='_compute_vehicle_counts')

    favorite_user_ids = fields.Many2many('res.users', default=_get_default_favorite_user_ids)
    is_favorite = fields.Boolean(
        compute='_compute_is_favorite', inverse='_inverse_is_favorite',
        string='Add to favorite',
        help='Whether this fleet is in your favorites or not.',
    )

    @api.depends('vehicle_ids')
    def _compute_vehicle_counts(self):
        for fleet in self:
            car_ids = fleet.vehicle_ids.filtered(lambda v: v.model_id.vehicle_type == 'car')
            fleet.car_count = len(car_ids)
            bike_ids = fleet.vehicle_ids - car_ids
            fleet.bike_count = len(bike_ids)

    def _compute_is_favorite(self):
        for fleet in self:
            fleet.is_favorite = self.env.user in fleet.favorite_user_ids

    def _inverse_is_favorite(self):
        # We may not have write access
        favorites = not_favorites = self.env['fleet.category'].sudo()
        for category in self:
            if self.env.user in category.favorite_user_ids:
                favorites |= category
            else:
                not_favorites |= category

        not_favorites.write({'favorite_user_ids': [(4, self.env.uid)]})
        favorites.write({'favorite_user_ids': [(3, self.env.uid)]})

    def toggle_active(self):
        res = super().toggle_active()
        archived = self.filtered(lambda c: not c.active)
        for category in archived:
            category.vehicle_ids.write({
                'fleet_id': False,
            })
        return res

    def action_view_vehicles(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fleet Vehicles'),
            'res_model': 'fleet.vehicle',
            'view_mode': 'tree,kanban,form',
            'views': [[False, 'list'], [False, 'kanban'], [False, 'form']],
            'domain': [('fleet_id', '=', self.id)],
            'context': {'default_fleet_id': self.id},
        }

    def write(self, vals):
        # directly compute is_favorite to dodge allow write access right
        if 'is_favorite' in vals:
            vals.pop('is_favorite')
            self._fields['is_favorite'].determine_inverse(self)
        return super().write(vals) if vals else True
