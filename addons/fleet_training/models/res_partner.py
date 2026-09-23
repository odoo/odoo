from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    fleet_training_driver_count = fields.Integer(
        string="Fleet Drivers", compute='_compute_fleet_training_driver_count',
    )

    @api.depends_context('uid')
    def _compute_fleet_training_driver_count(self):
        # This field shows up on every partner form. Only compute a real count
        # for users with Fleet Training access, so opening any other contact
        # never raises an AccessError for users outside the Fleet groups.
        self.fleet_training_driver_count = 0
        if not self.env.user.has_group('fleet_training.group_fleet_user'):
            return
        driver_data = self.env['fleet_training.driver']._read_group(
            [('partner_id', 'in', self.ids)], ['partner_id'], ['__count'],
        )
        counts = {partner.id: count for partner, count in driver_data}
        for partner in self:
            partner.fleet_training_driver_count = counts.get(partner.id, 0)
