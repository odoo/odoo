from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, AccessError


class CalendarCalendar(models.Model):
    _name = 'calendar.calendar'
    _description = 'User Calendar'

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)

        if 'calendar_user_ids' not in defaults and 'calendar_user_ids' in fields:
            defaults['calendar_user_ids'] = [Command.create({
                'user_id': self.env.user.id,
                'access_role': 'owner',
                'is_filter_active': True,
                'is_filter_checked': True,
                'name': _('Calendar')
            })]

        return defaults

    name = fields.Char(string='Name')
    event_ids = fields.One2many('calendar.event', 'calendar_id', "Events")
    recurrence_ids = fields.One2many('calendar.recurrence', 'calendar_id', "Recurrences")

    calendar_default_privacy = fields.Selection(
        [('public', 'Public by default'),
         ('private', 'Private by default'),
         ('confidential', 'Internal users only'),
         ('members_only', 'Calendar members only')],
        default=lambda self: self.env['ir.config_parameter'].sudo().get_str('calendar.default_privacy', 'public'),
        required=True,
    )

    # All user membership records of this calendar
    calendar_user_ids = fields.One2many('calendar.user', inverse_name='calendar_id', string='Users')
    owner_id = fields.Many2one('res.users', compute='_compute_owner_id')
    share_user_ids = fields.Many2many('res.users', string="Shared with", compute='_compute_share_user_ids',
        inverse='_inverse_share_user_ids', domain="[('id', '!=', owner_id), ('share', '=', False)]")
    # The current user's membership record of this calendar, if any
    calendar_user_id = fields.Many2one(
        'calendar.user',
        string='Current Membership Record',
        compute='_compute_calendar_user',
        search='_search_calendar_user_id',
    )
    color = fields.Integer(related='calendar_user_id.filter_color', readonly=False)
    is_primary = fields.Boolean(related='calendar_user_id.is_primary')
    """
    Access roles based on Google Calendar. The only roles managed in the base calendar module are:
        owner - has full access to the calendar, can read/write/delete events and change the calendar settings
       writer - can read/write/delete non-private events, but cannot edit settings like calendar privacy

    Other roles (reader, freeBusyReader) are managed in the google_calendar module, as they are not relevant
    to the base calendar module.
    """
    user_access_role = fields.Selection(related='calendar_user_id.access_role')

    def write(self, vals):
        """ Forbid the calendar default privacy update from different users for keeping private events secured. """
        if ('calendar_default_privacy' in vals and
                any(self.env.user != calendar.owner_id and not self.env.su for calendar in self)):
            raise AccessError(_("You are not allowed to change the default privacy of a calendar you do not own."))
        return super().write(vals)

    @api.depends_context('uid')
    @api.depends('calendar_user_ids')
    def _compute_calendar_user(self):
        """ Gets the calendar user record for the current user, if present."""
        for calendar in self:
            calendar.calendar_user_id = calendar.calendar_user_ids.filtered(lambda c: c.user_id == self.env.user)

    @api.model
    def _search_calendar_user_id(self, operator, value):
        return [('id', operator, self.calendar_user_ids.filtered(lambda c: c.user_id == self.env.user.id).ids)]

    @api.depends('calendar_user_ids.user_id', 'calendar_user_ids.access_role')
    def _compute_share_user_ids(self):
        for calendar in self:
            # Do not include the owner(s) in this list, as we do not want the user to be able to remove themselves.
            # Doing so could lead to accidental cascade deletion of the calendar
            calendar.share_user_ids = calendar.calendar_user_ids.filtered(lambda cu: cu.access_role != 'owner').user_id

    def _inverse_share_user_ids(self):
        for calendar in self:
            non_owner_calendar_users = calendar.calendar_user_ids.filtered(lambda cu: cu.access_role != 'owner')
            users_before = non_owner_calendar_users.user_id
            users_after = calendar.share_user_ids
            users_to_remove = users_before - users_after
            users_to_add = users_after - users_before

            if users_to_remove:
                non_owner_calendar_users.filtered(lambda cu: cu.user_id in users_to_remove).unlink()

            self.env['calendar.user'].create([{
                'access_role': 'writer',
                'calendar_id': calendar.id,
                'name': calendar.name,
                'user_id': user.id,
            } for user in users_to_add])

    @api.depends_context('uid')
    @api.depends('calendar_user_id')
    def _compute_display_name(self):
        for calendar in self:
            if self.env.user == calendar.owner_id:
                calendar.display_name = calendar.name
            else:
                calendar.display_name = calendar.calendar_user_id.name or calendar.name

    @api.depends('calendar_user_ids.access_role', 'calendar_user_ids.user_id')
    def _compute_owner_id(self):
        for calendar in self:
            calendar.owner_id = calendar.calendar_user_ids.filtered(lambda l: l.access_role == 'owner').user_id.id

    @api.ondelete(at_uninstall=False)
    def _unlink_except_primary(self):
        if self.calendar_user_ids.filtered('is_primary'):
            raise UserError(_("A primary calendar cannot be deleted."))

    def add_filter_to_list(self):
        self.calendar_user_id.is_filter_active = not self.calendar_user_id.is_filter_active
        self.calendar_user_id.is_filter_checked = True
