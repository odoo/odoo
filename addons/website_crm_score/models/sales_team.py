# -*- coding: utf-8 -*-
from openerp import fields, api, models
from openerp.osv import osv
from openerp.tools.safe_eval import safe_eval
from random import randint, shuffle
import datetime
import logging
import math

_logger = logging.getLogger(__name__)
evaluation_context = {
    'datetime': datetime,
    'context_today': datetime.datetime.now,
}

try:
    from flanker.addresslib import address

    def checkmail(mail):
        return bool(address.validate_address(mail))

except ImportError:
    _logger.warning('flanker not found, email validation disabled.')

    def checkmail(mail):
        return True


class team_user(models.Model):
    _name = 'team.user'

    @api.one
    def _count_leads(self):
        if self.id:
            limit_date = datetime.datetime.now() - datetime.timedelta(days=30)
            domain = [('user_id', '=', self.user_id.id),
                      ('team_id', '=', self.team_id.id),
                      ('assign_date', '>', fields.Datetime.to_string(limit_date))
                      ]
            self.leads_count = self.env['crm.lead'].search_count(domain)
        else:
            self.leads_count = 0

    @api.one
    def _get_percentage(self):
        try:
            self.percentage_leads = round(100 * self.leads_count / float(self.maximum_user_leads), 2)
        except ZeroDivisionError:
            self.percentage_leads = 0.0

    @api.one
    @api.constrains('team_user_domain')
    def _assert_valid_domain(self):
        try:
            domain = safe_eval(self.team_user_domain or '[]', evaluation_context)
            self.env['crm.lead'].search(domain)
        except Exception:
            raise Warning('The domain is incorrectly formatted')

    team_id = fields.Many2one('crm.team', string='SaleTeam', required=True, oldname='section_id')
    user_id = fields.Many2one('res.users', string='Saleman', required=True)
    name = fields.Char(related='user_id.partner_id.display_name')
    running = fields.Boolean(string='Running', default=True)
    team_user_domain = fields.Char('Domain')
    maximum_user_leads = fields.Integer('Leads Per Month')
    leads_count = fields.Integer('Assigned Leads', compute='_count_leads', help='Assigned Leads this last month')
    percentage_leads = fields.Float(compute='_get_percentage', string='Percentage leads')

    @api.one
    def toggle_active(self):
        if isinstance(self.id, int):  # if already saved
            self.running = not self.running


class crm_team(osv.osv):
    _inherit = "crm.team"

    @api.one
    def _count_leads(self):
        if self.id:
            self.leads_count = self.env['crm.lead'].search_count([('team_id', '=', self.id)])
        else:
            self.leads_count = 0

    @api.one
    def _assigned_leads(self):
        limit_date = datetime.datetime.now() - datetime.timedelta(days=30)
        domain = [('assign_date', '>=', fields.Datetime.to_string(limit_date)),
                  ('team_id', '=', self.id),
                  ('user_id', '!=', False)
                  ]
        self.assigned_leads = self.env['crm.lead'].search_count(domain)

    @api.one
    def _unassigned_leads(self):
        self.unassigned_leads = self.env['crm.lead'].search_count(
            [('team_id', '=', self.id), ('user_id', '=', False), ('assign_date', '=', False)]
        )

    @api.one
    def _capacity(self):
        self.capacity = sum(s.maximum_user_leads for s in self.team_user_ids)

    @api.one
    @api.constrains('score_team_domain')
    def _assert_valid_domain(self):
        try:
            domain = safe_eval(self.score_team_domain or '[]', evaluation_context)
            self.env['crm.lead'].search(domain)
        except Exception:
            raise Warning('The domain is incorrectly formatted')

    ratio = fields.Float(string='Ratio')
    score_team_domain = fields.Char('Domain')
    leads_count = fields.Integer(compute='_count_leads')
    assigned_leads = fields.Integer(compute='_assigned_leads')
    unassigned_leads = fields.Integer(compute='_unassigned_leads')
    capacity = fields.Integer(compute='_capacity')
    team_user_ids = fields.One2many('team.user', 'team_id', string='Salesman')
    min_for_assign = fields.Integer("Minimum score", help="Minimum score to be automatically assign (>=)", default=0, required=True)

    @api.model
    def direct_assign_leads(self, ids=[]):
        ctx = dict(self._context, mail_notify_noemail=True)
        self.with_context(ctx)._assign_leads()

    @api.model
    def dry_assign_leads(self, ids=[]):
        self._assign_leads(dry=True)

    @api.model
    # Note: The dry mode assign only 50 leads per salesteam for speed issues
    def assign_leads_to_salesteams(self, all_salesteams, dry=False):
        shuffle(all_salesteams)
        haslead = True

        while haslead:
            haslead = False
            for salesteam in all_salesteams:
                domain = safe_eval(salesteam['score_team_domain'], evaluation_context)
                domain.extend([('team_id', '=', False), ('user_id', '=', False)])
                domain.extend(['|', ('stage_id.on_change', '=', False), '&', ('stage_id.probability', '!=', 0), ('stage_id.probability', '!=', 100)])
                leads = self.env["crm.lead"].search(domain, limit=50)
                haslead = haslead or (len(leads) == 50 and not dry)

                if not leads.exists():
                    continue

                if dry:
                    for lead in leads:
                        values = {'lead_id': lead.id, 'team_id': salesteam['id']}
                        self.env['crm.leads.dry.run'].create(values)
                else:
                    leads.write({'team_id': salesteam['id']})

                    # Erase fake/false email
                    spams = map(lambda x: x.id, filter(lambda x: x.email_from and not checkmail(x.email_from), leads))

                    if spams:
                        self.env["crm.lead"].browse(spams).write({'email_from': False})

                    # Merge duplicated lead
                    leads_done = set()
                    for lead in leads:
                        if lead.id not in leads_done:
                            leads_duplicated = lead.get_duplicated_leads(False)
                            if len(leads_duplicated) > 1:
                                self.env["crm.lead"].browse(leads_duplicated).merge_opportunity(False, False)
                            leads_done.update(leads_duplicated)
                        self._cr.commit()
                self._cr.commit()

    @api.model
    def assign_leads_to_salesmen(self, all_team_users, dry=False):
        users = []
        for su in all_team_users:
            if (su.maximum_user_leads - su.leads_count) <= 0:
                continue
            domain = safe_eval(su.team_user_domain or '[]', evaluation_context)
            domain.extend([
                ('user_id', '=', False),
                ('assign_date', '=', False),
                ('score', '>=', su.team_id.min_for_assign)
            ])

            # assignation rythm: 2 days of leads if a lot of leads should be assigned
            limit = int(math.ceil(su.maximum_user_leads / 15.0))

            if dry:
                dry_leads = self.env["crm.leads.dry.run"].search([('team_id', '=', su.team_id.id)])
                domain.append(['id', 'in', dry_leads.mapped('lead_id.id')])
            else:
                domain.append(('team_id', '=', su.team_id.id))

            leads = self.env["crm.lead"].search(domain, order='score desc', limit=limit * len(su.team_id.team_user_ids))
            users.append({
                "su": su,
                "nbr": min(su.maximum_user_leads - su.leads_count, limit),
                "leads": leads
            })

        assigned = set()
        while users:
            i = 0

            # statistically select the user that should receive the next lead
            idx = randint(0, reduce(lambda nbr, x: nbr + x['nbr'], users, 0) - 1)

            while idx > users[i]['nbr']:
                idx -= users[i]['nbr']
                i += 1
            user = users[i]

            # Get the first unassigned leads available for this user
            while user['leads'] and user['leads'][0] in assigned:
                user['leads'] = user['leads'][1:]
            if not user['leads']:
                del users[i]
                continue

            # lead convert for this user
            lead = user['leads'][0]
            assigned.add(lead)
            if dry:
                values = {'lead_id': lead.id, 'team_id': user['su'].team_id.id, 'user_id': user['su'].user_id.id}
                self.env['crm.leads.dry.run'].create(values)
            else:
                # Assign date will be setted by write function
                data = {'user_id': user['su'].user_id.id}
                lead.write(data)

                lead.convert_opportunity(lead.partner_id and lead.partner_id.id or None)
                self._cr.commit()

            user['nbr'] -= 1
            if not user['nbr']:
                del users[i]

    @api.model
    def _assign_leads(self, dry=False):
        # Emptying the table
        self._cr.execute("""
                TRUNCATE TABLE crm_leads_dry_run;
            """)

        all_salesteams = self.search_read(fields=['score_team_domain'], domain=[('score_team_domain', '!=', False)])

        all_team_users = self.env['team.user'].search([('running', '=', True)])

        self.env['website.crm.score'].assign_scores_to_leads()

        self.assign_leads_to_salesteams(all_salesteams, dry=dry)

        # Compute score after assign to salesteam, because if a merge has been done, the score for leads is removed.
        self.env['website.crm.score'].assign_scores_to_leads()

        self.assign_leads_to_salesmen(all_team_users, dry=dry)
