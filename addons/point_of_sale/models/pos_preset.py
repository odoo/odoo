from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from collections import defaultdict


class PosPreset(models.Model):
    _name = 'pos.preset'
    _inherit = ['pos.load.mixin']
    _description = 'Easily load a set of configuration options'

    name = fields.Char(string='Label', required=True, translate=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position')
    identification = fields.Selection([('none', 'Not required'), ('address', 'Address'), ('name', 'Name')], default="none", string='Identification', required=True)
    is_return = fields.Boolean(string='Return mode', default=False, help="All quantity in the cart will be in negative. Ideal for return managment.")
    color = fields.Integer(string='Color', default=0)
    image_512 = fields.Image(string='Image', max_width=512, max_height=512)
    image_128 = fields.Image(string='Image 128', related="image_512", max_width=128, max_height=128, store=True)
    has_image = fields.Boolean(compute='_compute_has_image')
    count_linked_orders = fields.Integer(compute='_compute_count_linked_orders')
    count_linked_config = fields.Integer(compute='_compute_count_linked_config')

    # Timing options
    use_timing = fields.Boolean(string='Manage orders by time', default=False)
    resource_calendar_id = fields.Many2one('resource.calendar', 'Resource')
    attendance_ids = fields.One2many(related="resource_calendar_id.attendance_ids", string="Attendances", readonly=False)
    slots_per_interval = fields.Integer(string='Capacity', default=5)
    interval_time = fields.Integer(string='Interval time (in min)', default=20)

    @api.constrains('attendance_ids')
    def _check_slots(self):
        for preset in self:
            for attendance in preset.attendance_ids:
                if attendance.hour_from % 24 >= attendance.hour_to % 24:
                    raise ValidationError(_('The start time must be before the end time.'))

    @api.model
    def _load_pos_data_domain(self, data, config):
        preset_ids = config.available_preset_ids.ids + [config.default_preset_id.id]
        return [('id', 'in', preset_ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'pricelist_id', 'fiscal_position_id', 'is_return', 'color', 'has_image', 'write_date', 'identification',
            'use_timing', 'slots_per_interval', 'interval_time', 'attendance_ids']

    def _compute_count_linked_orders(self):
        for record in self:
            record.count_linked_orders = self.env['pos.order'].search_count([('preset_id', 'in', record.ids)])

    def _compute_count_linked_config(self):
        for record in self:
            record.count_linked_config = self.env['pos.config'].search_count([
                '|', ('default_preset_id', 'in', record.ids),
                ('available_preset_ids', 'in', record.ids)
            ])

    @api.depends('has_image')
    def _compute_has_image(self):
        for record in self:
            record.has_image = bool(record.image_512)

    # Slots are created directly here in the form of dates, to avoid polluting
    # the database with a “slots” model. All we need is the slot time, and with the preset
    # information we can deduce the maximum occupancy per slot.
    def get_available_slots(self):
        self.ensure_one()
        usage = self._compute_slots_usage()
        return {
            'usage_utc': usage,
        }

    def _compute_slots_usage(self):
        usage = defaultdict(int)
        orders = self.env['pos.order'].search([
            ('preset_id', '=', self.id),
            ('session_id.state', '=', 'opened'),
            ('preset_time', '!=', False),
            ('state', 'in', ['draft', 'paid']),
            ('create_date', '>=', fields.Datetime.now() - timedelta(days=1))
        ])
        for order in orders:
            sql_datetime_str = order.preset_time.strftime("%Y-%m-%d %H:%M:%S")

            if not usage[sql_datetime_str]:
                usage[sql_datetime_str] = []

            usage[sql_datetime_str].append(order.id)

        return usage

    def action_open_linked_orders(self):
        self.ensure_one()
        return {
            'name': _('Linked Orders'),
            'view_mode': 'list',
            'res_model': 'pos.order',
            'type': 'ir.actions.act_window',
            'domain': [('preset_id', '=', self.id)],
        }

    def action_open_linked_config(self):
        self.ensure_one()
        return {
            'name': _('Linked POS Configurations'),
            'view_mode': 'list',
            'res_model': 'pos.config',
            'type': 'ir.actions.act_window',
            'domain': ['|', ('default_preset_id', '=', self.id), ('available_preset_ids', 'in', self.id)]
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_preset(self):
        for preset in self:
            if preset.count_linked_config:
                raise UserError(_('You cannot delete a preset that is linked to a POS configuration.'))
