from odoo import api, fields, models


class EventTypeMail(models.Model):
    """ Template of event.mail to attach to event.type. Those will be copied
    upon all events created in that type to ease event creation. """
    _name = 'event.type.mail'
    _description = 'Mail Scheduling on Event Category'

    event_type_id = fields.Many2one(
        'event.type', string='Event Type',
        ondelete='cascade', required=True)
    interval_nbr = fields.Integer('Interval', default=1)
    interval_unit = fields.Selection([
        ('now', 'Immediately'),
        ('hours', 'Hours'), ('days', 'Days'),
        ('weeks', 'Weeks'), ('months', 'Months')],
        string='Unit', default='hours', required=True)
    interval_type = fields.Selection([
        # attendee based
        ('after_sub', 'After each registration'),
        # event based: start date
        ('before_event', 'Before the event starts'),
        ('after_event_start', 'After the event started'),
        # event based: end date
        ('after_event', 'After the event ended'),
        ('before_event_end', 'Before the event ends')],
        string='Trigger', default="before_event", required=True)
    notification_type = fields.Selection([('mail', 'Mail')], string='Send', compute='_compute_notification_type')
    template_ref = fields.Reference(string='Template', ondelete={'mail.template': 'cascade'}, required=True, selection=[('mail.template', 'Mail')])

    @api.depends('template_ref')
    def _compute_notification_type(self):
        """Assigns the type of template in use, if any is set."""
        self.notification_type = 'mail'

    def _prepare_event_mail_values(self):
        self.ensure_one()
        return {
            'interval_nbr': self.interval_nbr,
            'interval_unit': self.interval_unit,
            'interval_type': self.interval_type,
            'template_ref': '%s,%i' % (self.template_ref._name, self.template_ref.id),
        }
