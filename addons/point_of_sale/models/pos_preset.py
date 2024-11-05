from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from collections import defaultdict


class PosPreset(models.Model):
    _inherit = ['pos.load.mixin']
    _description = 'Easily load a set of configuration options'

    name = fields.Char(string='Label', required=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position')
    address_on_ticket = fields.Boolean(string='Print address on ticket', default=False)
    color = fields.Integer(string='Color', default=0)

    # Timing options
    hour_opening = fields.Float(string='Opening hour', default=18.0, help="Opening hour for the preset.")
    hour_closing = fields.Float(string='Closing hour', default=22.0, help="Closing hour for the preset.")
    use_timing = fields.Boolean(string='Timing', default=False)
    capacity_per_x_minutes = fields.Integer(string='Capacity', default=5)
    x_minutes = fields.Integer(string='Minutes', default=20)
    preparation_time_minute = fields.Integer(string='Preparation Time', default=5)

    @api.model
    def _load_pos_data_domain(self, data):
        preset_ids = data['pos.config']['data'][0]['available_preset_ids'] + [data['pos.config']['data'][0]['default_preset_id']]
        return [('id', 'in', preset_ids)]

    def write(self, vals):
        config_ids = self.env['pos.config'].search_count([
            ('has_active_session', '=', True),
            ('default_preset_id', 'in', self.ids),
            ('available_preset_ids', 'in', self.ids)])

        if config_ids:
            raise UserError(_('You cannot modify a preset that is currently in use by a PoS session.'))

        return super().write(vals)

    # Slots are created directly here in the form of dates, to avoid polluting
    # the database with a “slots” model. All we need is the slot time, and with the preset
    # information we can deduce the maximum occupancy per slot.
    def get_available_slots(self):
        self.ensure_one()
        usage = self._compute_slots_usage()
        date_now = datetime.now()
        interval = timedelta(minutes=self.x_minutes)
        date_now_opening = datetime(date_now.year, date_now.month, date_now.day, int(self.hour_opening), int((self.hour_opening % 1) * 60))
        date_now_closing = datetime(date_now.year, date_now.month, date_now.day, int(self.hour_closing), int((self.hour_closing % 1) * 60))
        slots = []

        start = date_now_opening
        keeper = 0
        while start <= date_now_closing and keeper < 1000:
            slots.append({
                'datetime': start,
                'sql_datetime': start.strftime("%Y-%m-%d %H:%M:%S"),
                'humain_readable': start.strftime("%H:%M"),
            })
            keeper += 1
            start += interval

        for slot in slots:
            slot['order_ids'] = usage.get(slot['sql_datetime'], [])

        return slots

    def _compute_slots_usage(self):
        usage = defaultdict(int)
        orders = self.env['pos.order'].search([
            ('preset_id', '=', self.id),
            ('session_id.state', '=', 'opened'),
            ('state', 'in', ['draft', 'paid', 'invoiced']),
        ])
        for order in orders:
            sql_datetime_str = order.preset_time.strftime("%Y-%m-%d %H:%M:%S")

            if not usage[sql_datetime_str]:
                usage[sql_datetime_str] = []

            usage[sql_datetime_str].append(order.id)

        return usage
