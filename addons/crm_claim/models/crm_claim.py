# -*- coding: utf-8 -*-

from openerp import api, fields, models, tools, _
from openerp.addons.base.res.res_request import referencable_models


class CrmClaimStage(models.Model):

    """ Model for claim stages. This models the main stages of a claim
        management flow. Main CRM objects (leads, opportunities, project
        issues, ...) will now use only stages, instead of state and stages.
        Stages are for example used to display the kanban view of records.
    """
    _name = "crm.claim.stage"
    _description = "Claim stages"
    _order = "sequence"

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(default=1, help="Used to order stages. Lower is better.")
    team_ids = fields.Many2many(
        'crm.team', 'crm_team_claim_stage_rel', 'stage_id', 'team_id',
        string='Teams', help="Link between stages and sales teams. When set, this limitate the current stage to the selected sales teams.")
    case_default = fields.Boolean(
        string='Common to All Teams',
        help="If you check this field, this stage will be proposed by default on each sales team. It will not assign this stage to existing teams.")


class CrmClaim(models.Model):

    """ Crm claim
    """
    _name = "crm.claim"
    _description = "Claim"
    _inherit = 'mail.thread'
    _order = "priority,date desc"

    name = fields.Char(string='Claim Subject', required=True)
    active = fields.Boolean(default=True)
    action_next = fields.Char(string='Next Action')
    date_action_next = fields.Datetime(string='Next Action Date')
    description = fields.Text()
    resolution = fields.Text()
    create_date = fields.Datetime(string='Creation Date', readonly=True)
    write_date = fields.Datetime(string='Update Date', readonly=True)
    date_deadline = fields.Date(string='Deadline')
    date_closed = fields.Datetime(string='Closed', readonly=True)
    date = fields.Datetime(string='Claim Date', index=True, default=fields.Datetime.now)
    ref = fields.Reference(selection=lambda self: referencable_models(self, self.env.cr, self.env.uid, self.env.context), string='Reference')
    categ_id = fields.Many2one('crm.claim.category', string='Category')
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], default='1')
    type_action = fields.Selection([('correction', 'Corrective Action'), ('prevention', 'Preventive Action')], string='Action Type')
    user_id = fields.Many2one('res.users', string='Responsible', track_visibility='always', default=lambda self: self.env.user)
    user_fault = fields.Char(string='Trouble Responsible')
    team_id = fields.Many2one(
        'crm.team', string='Sales Team', oldname='section_id', index=True,
        default=lambda self: self.env['crm.lead']._resolve_team_id_from_context() or False,
        help="Responsible sales team. Define Responsible user and Email account for mail gateway.")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('crm.case'))
    partner_id = fields.Many2one('res.partner', string='Partner')
    email_cc = fields.Text(
        string='Watchers Emails',
        help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. \
        Separate multiple email addresses with a comma")
    email_from = fields.Char(string='Email', size=128, help="Destination email for email gateway.")
    partner_phone = fields.Char(string='Phone')
    stage_id = fields.Many2one(
        'crm.claim.stage', string='Stage', track_visibility='onchange',
        default=lambda self: self.stage_find([], self.team_id, [('sequence', '=', '1')]),
        domain="['|', ('team_ids', '=', team_id), ('case_default', '=', True)]")
    cause = fields.Text(string='Root Cause')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.email_from = self.partner_id.email
        self.partner_phone = self.partner_id.phone

    @api.model
    def create(self, vals):
        if vals.get('team_id') and not self.env.context.get('default_team_id'):
            return super(CrmClaim, self.with_context(default_team_id=vals.get('team_id'))).create(vals)
        return super(CrmClaim, self).create(vals)

    @api.one
    def copy(self, default={}):
        team_id = self.env['crm.lead']._resolve_team_id_from_context() or False
        default.update({
            'stage_id': self.stage_find([], team_id, [('sequence', '=', '1')]),
            'name': _('%s (copy)') % (self.name)})
        return super(CrmClaim, self).copy(default=default)

    @api.model
    def stage_find(self, cases, team_id, domain=[], order='sequence'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - team_id: if set, stages must belong to this team or
              be a default case
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cases)
        search_domain = ([('team_ids', '=', team_id)] if team_id else []) + ([('team_ids', '=', claim.team_id.id) for claim in cases if claim.team_id])
        search_domain = ['|'] * len(search_domain) + search_domain + [('case_default', '=', True)] + domain
        return self.env['crm.claim.stage'].search(search_domain, order=order, limit=1)

    # -------------------------------------------------------
    # Mail gateway
    # -------------------------------------------------------

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if not custom_values:
            custom_values = {}
        desc = tools.html2plaintext(msg.get('body')) if msg.get('body') else ''
        defaults = {
            'name': msg.get('subject') or _("No Subject"),
            'description': desc,
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
        }
        if msg.get('priority'):
            defaults['priority'] = msg.get('priority')
        defaults.update(custom_values)
        return super(CrmClaim, self).message_new(msg, custom_values=defaults)


class CrmClaimCategory(models.Model):

    _name = "crm.claim.category"
    _description = "Category of claim"

    name = fields.Char(required=True, translate=True)
    team_id = fields.Many2one('crm.team', string='Sales Team')
