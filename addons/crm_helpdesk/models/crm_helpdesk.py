# -*- coding: utf-8 -*-

from openerp import _, api, fields, models
from openerp.exceptions import UserError
from openerp.tools import html2plaintext


class CrmHelpdesk(models.Model):
    """ Helpdesk Cases """

    _name = "crm.helpdesk"
    _description = "Helpdesk"
    _order = "id desc"
    _inherit = ['mail.thread']

    id = fields.Integer(string='ID', readonly=True)
    name = fields.Char(required=True)
    active = fields.Boolean(required=False, default=True)
    date_action_last = fields.Datetime(string='Last Action', readonly=True)
    date_action_next = fields.Datetime(string='Next Action', readonly=True)
    description = fields.Text()
    create_date = fields.Datetime(string='Creation Date', readonly=True)
    write_date = fields.Datetime(string='Update Date', readonly=True)
    date_deadline = fields.Date(string='Deadline')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.uid)
    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id',\
                    index=True, help='Responsible sales team. Define Responsible user and Email account for mail gateway.')
    company_id = fields.Many2one('res.company', string='Company', 
                    default=lambda self: self.env['res.company']._company_default_get('crm.helpdesk'))
    date_closed = fields.Datetime(string='Closed', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    email_cc = fields.Text(string='Watchers Emails', size=252,
                    help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma")
    email_from = fields.Char(string='Email', size=128,
                    help="Destination email for email gateway")
    date = fields.Datetime()
    ref = fields.Reference(string='Reference', selection='referencable_models')
    ref2 = fields.Reference(string='Reference 2', selection='referencable_models')
    channel_id = fields.Many2one('utm.medium', string='Channel',
                    help="Communication channel.")
    planned_revenue = fields.Float()
    planned_cost = fields.Float(string='Planned Costs')
    priority = fields.Selection([('0', 'Low'),
                                ('1', 'Normal'),
                                ('2', 'High')], default='1')
    probability = fields.Float(string='Probability (%)')
    categ_id = fields.Many2one('crm.helpdesk.category', string='Category')
    duration = fields.Float(string='Duration', states={'done': [('readonly', True)]})
    state = fields.Selection([('draft', 'New'),
                             ('open', 'In Progress'),
                             ('pending', 'Pending'),
                             ('done', 'Closed'),
                             ('cancel', 'Cancelled')],
                            string='Status', default='draft', readonly=True, track_visibility='onchange',
                    help='The status is set to \'Draft\', when a case is created.\
                    \nIf the case is in progress the status is set to \'Open\'.\
                    \nWhen the case is over, the status is set to \'Done\'.\
                    \nIf the case needs to be reviewed then the status is set to \'Pending\'.')


    @api.model
    def referencable_models(self):
        return [(r['object'], r['name']) for r in self.env['res.request.link'].search([])]

    @api.onchange('partner_id')
    def on_change_partner_id(self):
            self.email_from = self.partner_id.email

    @api.multi
    def write(self, values):
        """ Override to add case management: open/close dates """
        if values.get('state'):
            if values.get('state') in ['draft', 'open'] and not values.get('date_open'):
                values['date_open'] = fields.datetime.now()
            elif values.get('state') == 'close' and not values.get('date_closed'):
                values['date_closed'] = fields.datetime.now()
        return super(CrmHelpdesk, self).write(values)

    @api.one
    def case_escalate(self):
        """ Escalates case to parent level """
        data = {}
        if self.team_id and self.team_id.parent_id:
            parent_id = self.team_id.parent_id
            data['team_id'] = parent_id.id
            if parent_id.change_responsible and parent_id.user_id:
                data['user_id'] = parent_id.user_id.id
            self.write(data)
        else:
            raise UserError(_('You can not escalate, \
                you are already at the top level regarding your sales-team category.'))

    # -------------------------------------------------------
    # Mail gateway
    # -------------------------------------------------------

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        desc = html2plaintext(msg.get('body')) if msg.get('body') else ''
        defaults = {
            'name': msg.get('subject') or _("No Subject"),
            'description': desc,
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'user_id': False,
            'partner_id': msg.get('author_id', False),
        }
        defaults.update(custom_values)
        return super(CrmHelpdesk, self).message_new(msg, custom_values=defaults)


class CrmHelpdeskCategory(models.Model):
    _name = "crm.helpdesk.category"
    _description = "Helpdesk Category"

    name = fields.Char(required=True, translate=True)
    team_id = fields.Many2one('crm.team', string='Sales Team')
