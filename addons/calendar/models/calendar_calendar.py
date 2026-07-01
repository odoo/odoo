from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, AccessError


class CalendarCalendar(models.Model):
    _name = 'calendar.calendar'
    _description = 'Calendar'

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)

        if 'calendar_default_privacy' not in defaults and 'calendar_default_privacy' in fields:
            user_id = defaults.get('user_id')
            if not user_id:
                return defaults

            user = self.env['res.users'].browse(user_id)
            privacy = user.sudo().res_users_settings_id.calendar_default_privacy
            privacy_fallback = self.env['ir.config_parameter'].sudo().get_str('calendar.default_privacy', 'public')
            defaults['calendar_default_privacy'] = privacy or privacy_fallback

        if 'calendar_users' not in defaults and 'calendar_users' in fields:
            defaults['calendar_users'] = [Command.create({
                'user_id': self.env.user.id,
                'access_role': 'owner',
                'is_filter_active': True,
                'is_filter_checked': True,
                'label': 'Calendar'
            })]

        return defaults

    calendar_user = fields.Many2one('calendar.calendar.user', compute='_compute_calendar_user')
    color = fields.Integer(string='Color', compute='_compute_color', inverse='_inverse_color')
    event_ids = fields.One2many('calendar.event', 'calendar_id', "Events")
    recurrence_ids = fields.One2many('calendar.recurrence', 'calendar_id', "Recurrences")
    is_primary = fields.Boolean('Primary Calendar', compute="_compute_is_primary")
    name = fields.Char('Name', compute='_compute_name', inverse='_inverse_name')
    calendar_users = fields.One2many('calendar.calendar.user', inverse_name='calendar_id', string='Users')
    owners = fields.Many2many('res.users', compute='_compute_owners')
    user_access_role = fields.Selection([
        ('owner', 'owner'),
        ('writer', 'write'),
        ('reader', 'read'),
        ('freeBusyReader', 'freeBusyReader'),
        ('none', 'none')],
        compute='_compute_user_access_role')
    user_has_read_access = fields.Boolean(compute='_compute_user_has_read_access', search="_search_user_has_read_access")
    user_has_write_access = fields.Boolean(compute='_compute_user_has_write_access', search="_search_user_has_write_access")
    calendar_default_privacy = fields.Selection(
        [('public', 'Public by default'),
         ('private', 'Private by default'),
         ('confidential', 'Internal users only')],
        default='private',
    )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_primary(self):
        if any(calendar.calendar_users.is_primary for calendar in self):
            raise UserError(_("A primary calendar cannot be deleted."))

    def write(self, vals):
        """ Forbid the calendar default privacy update from different users for keeping private events secured. """
        if 'calendar_default_privacy' in vals:
            if any(self.env.user not in calendar.owners for calendar in self):
                raise AccessError(
                    _("You are not allowed to change the calendar default privacy of another user due to privacy constraints."))
        return super().write(vals)

    @api.depends_context('uid')
    def _compute_calendar_user(self):
        for calendar in self:
            user_calendar = self.env['calendar.calendar.user'].search([
                ('calendar_id', 'in', calendar.ids),
                ('user_id', '=', self.env.uid),
            ], limit=1)
            calendar.calendar_user = user_calendar

    @api.depends_context('uid')
    @api.depends('calendar_users.filter_color')
    def _compute_name(self):
        for calendar in self:
            calendar.name = calendar.calendar_user.label

    def _inverse_name(self):
        for calendar in self:
            if calendar.calendar_user:
                calendar.calendar_user.label = calendar.name

    @api.depends('calendar_users.access_role', 'calendar_users.user_id')
    def _compute_owners(self):
        for calendar in self:
            calendar.owners = calendar.calendar_users.filtered(lambda l: l.access_role == 'owner').mapped('user_id')

    @api.depends_context('uid')
    @api.depends('calendar_users.filter_color')
    def _compute_color(self):
        for calendar in self:
            calendar.color = calendar.calendar_user.filter_color if calendar.calendar_user else 1

    def _inverse_color(self):
        for calendar in self:
            if calendar.calendar_user:
                calendar.calendar_user.filter_color = calendar.color

    @api.depends('calendar_users')
    def _compute_is_primary(self):
        for calendar in self:
            calendar.is_primary = calendar.calendar_user.is_primary

    @api.depends_context('uid')
    @api.depends('calendar_users.access_role')
    def _compute_user_access_role(self):
        for calendar in self:
            # New records which are not yet saved should be assigned a default role.
            if not calendar.id:
                calendar.user_access_role = 'owner'
                continue
            # sudo() needed to avoid circular evaluation with the record rule,
            calendar.user_access_role = calendar.sudo().calendar_users.filtered(
                lambda l: l.user_id == self.env.user).access_role or 'none'

    @api.depends_context('uid')
    @api.depends('user_access_role')
    def _compute_user_has_read_access(self):
        for calendar in self:
            calendar.user_has_read_access = calendar.user_access_role in ('owner', 'writer', 'reader', 'freeBusyReader')

    @api.depends_context('uid')
    @api.depends('user_access_role')
    def _compute_user_has_write_access(self):
        for calendar in self:
            calendar.user_has_write_access = calendar.user_access_role in ('owner', 'writer')

    def _search_user_has_read_access(self, operator, value):
        # The ORM will optimize the domain leaf
        # before calling the search method:
        # = True | != False -> in [True]
        # != True | = False -> not in [True]
        if operator not in ('in', 'not in'):
            return NotImplemented

        accessible_calendar_ids = self.env['calendar.calendar.user'].sudo().search([
            ('user_id', '=', self.env.uid),
        ]).calendar_id.ids

        return [('id', operator, accessible_calendar_ids)]

    def _search_user_has_write_access(self, operator, value):
        if operator not in ('in', 'not in'):
            return NotImplemented

        writable_calendar_ids = self.env['calendar.calendar.user'].sudo().search([
            ('user_id', '=', self.env.uid),
            ('access_role', 'in', ('owner', 'writer')),
        ]).calendar_id.ids

        return [('id', operator, writable_calendar_ids)]
