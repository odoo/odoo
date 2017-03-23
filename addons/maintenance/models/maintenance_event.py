from odoo import api, fields, models, _


class MaintenanceAttendee(models.Model):
    _name = 'maintenance.attendee'
    _inherit = 'calendar.attendee'
    event_id = fields.Many2one('maintenance.event', 'Meeting linked', ondelete='cascade')

    # We override this method in order to don't send mail.
    @api.multi
    def _send_mail_to_attendees(self, template_xmlid, force_send=False):
        return True


class MaintenanceMeeting(models.Model):

    @api.model
    def _default_partners(self):
        """ When active_model is res.partner, the current partners should be attendees """
        partners = self.env.user.partner_id
        active_id = self._context.get('active_id')
        if self._context.get('active_model') == 'res.partner' and active_id:
            if active_id not in partners.ids:
                partners |= self.env['res.partner'].browse(active_id)
        return partners

    """ Model for Maintenance Calendar Event """
    _name = 'maintenance.event'
    _inherit = 'calendar.event'

    maintenance_id = fields.One2many('maintenance.request', 'calendar', string="Linked maintenance request", copy=False)
    description = fields.Text('Description', related='maintenance_id.description')
    owner_user_id = fields.Many2one('res.users', string='Created by', related='maintenance_id.owner_user_id')
    equipment_id = fields.Many2one('maintenance.equipment', string='Equipment', related='maintenance_id.equipment_id')
    category_id = fields.Many2one('maintenance.equipment.category', related='maintenance_id.category_id', string='Category', readonly=True)
    request_date = fields.Date('Request Date', related='maintenance_id.request_date')
    close_date = fields.Date('Close Date', help="Date the maintenance was finished.", related='maintenance_id.close_date')
    maintenance_type = fields.Selection([('corrective', 'Corrective'), ('preventive', 'Preventive')], related='maintenance_id.maintenance_type')
    maintenance_team_id = fields.Many2one('maintenance.team', related='maintenance_id.maintenance_team_id')
    technician_user_id = fields.Many2one('res.users', related='maintenance_id.technician_user_id')
    # Mandatory field to override for calendar inheritance
    categ_ids = fields.Many2many('calendar.event.type', 'maintenance_category_rel', 'event_id', 'type_id', 'Tags')
    partner_ids = fields.Many2many('res.partner', 'maintenance_event_res_partner_rel', string='Attendees', copy=False)
    alarm_ids = fields.Many2many('calendar.alarm', 'calendar_alarm_maintenance_event_rel', string='Reminders', ondelete="restrict", copy=False)
    attendee_ids = fields.One2many('maintenance.attendee', 'event_id', 'Participant', ondelete='cascade', copy=False)

    # This method is used when you create a maintenance request directly from the maintenance event views
    @api.model
    def create(self, vals):
        calendar = super(MaintenanceMeeting, self).create(vals)
        if calendar.maintenance_id.exists():
            self.env['maintenance.request'].create({
                'name': calendar.name,
                'calendar': calendar.id,
            })
        return calendar
