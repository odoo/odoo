from openerp.osv import osv
from openerp import fields, api, models
import datetime
from openerp.tools.safe_eval import safe_eval
from random import randint, shuffle
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
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
    _logger.warning('Flanker library not found, Flanker features (check email on lead) disabled. If you plan to use it, please install the Flanker library from http://pypi.python.org/pypi/flanker')

    def checkmail(mail):
        return True


class crm_case_section(osv.osv):
    _inherit = "crm.case.section"

    @api.one
    def _count_leads(self):
        if self.id:
            self.leads_count = self.env['crm.lead'].search_count([('section_id', '=', self.id)])
        else:
            self.leads_count = 0

    @api.one
    def _assigned_leads(self):
        limit_date = datetime.datetime.now() - datetime.timedelta(days=30)
        domain = [('assign_date', '>=', limit_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                  ('section_id', '=', self.id),
                  ('user_id', '!=', False)
                  ]
        self.assigned_leads = self.env['crm.lead'].search_count(domain)

    @api.one
    def _unassigned_leads(self):
        self.unassigned_leads = self.env['crm.lead'].search_count([('section_id', '=', self.id), ('user_id', '=', False), ('assign_date', '=', False)])

    @api.one
    def _capacity(self):
        self.capacity = sum(s.maximum_user_leads for s in self.section_user_ids)

    @api.one
    @api.constrains('score_section_domain')
    def _assert_valid_domain(self):
        try:
            domain = safe_eval(self.score_section_domain or '[]', evaluation_context)
            self.env['crm.lead'].search(domain)
        except Exception:
            raise Warning('The domain is incorrectly formatted')

    ratio = fields.Float(string='Ratio')
    score_section_domain = fields.Char('Domain')
    leads_count = fields.Integer(compute='_count_leads')
    assigned_leads = fields.Integer(compute='_assigned_leads')
    unassigned_leads = fields.Integer(compute='_unassigned_leads')
    capacity = fields.Integer(compute='_capacity')
    section_user_ids = fields.One2many('section.user', 'section_id', string='Salesman')
    min_for_assign = fields.Integer("Minimum score", help="Minimum Score for a lead to be automatically assign (>=)", default=0, required=True)

    @api.model
    def score_and_assign_leads(self):
        self.env['website.crm.score'].assign_scores_to_leads()
        self._assign_leads()

    @api.model
    def direct_assign_leads(self, ids=[]):
        self._assign_leads()

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
                domain = safe_eval(salesteam['score_section_domain'], evaluation_context)
                domain.extend([('section_id', '=', False), ('user_id', '=', False)])
                leads = self.env["crm.lead"].search(domain, limit=50)
                haslead = haslead or (len(leads) == 50 and not dry)
                if dry:
                    for lead in leads:
                        values = {'lead_id': lead.id, 'section_id': salesteam['id']}
                        self.env['leads.dry.run'].create(values)
                else:
                    leads.write({'section_id': salesteam['id']})

                    # Erase fake/false email
                    spams = map(lambda x: x.id, filter(lambda x: x.email_from and not checkmail(x.email_from), leads))
                    self.env["crm.lead"].browse(spams).write({'email_from': False})

                    # Merge duplicated lead
                    leads_done = []
                    for lead in leads:
                        if lead.id not in leads_done:
                            leads_duplicated = lead.get_duplicated_leads(False)
                            if len(leads_duplicated) > 1:
                                self.env["crm.lead"].browse(leads_duplicated).merge_opportunity(False, False)
                            leads_done += leads_duplicated
        self._cr.commit()

    @api.model
    def assign_leads_to_salesmen(self, all_section_users, dry=False):
        users = []
        for su in all_section_users:
            if (su.maximum_user_leads - su.leads_count) <= 0:
                continue
            domain = safe_eval(su.section_user_domain or '[]', evaluation_context)
            domain.append(('user_id', '=', False))
            domain.append(('assign_date', '=', False))
            domain.append(('score', '>=', su.section_id.min_for_assign))

            # assignation rythm: 2 days of leads if a lot of leads should be assigned
            limit = int(math.ceil(su.maximum_user_leads / 15.0))

            if dry:
                dry_leads = self.env["leads.dry.run"].search([('section_id', '=', su.section_id.id)])
                domain.append(['id', 'in', [dl.lead_id.id for dl in dry_leads]])
            else:
                domain.append(('section_id', '=', su.section_id.id))

            leads = self.env["crm.lead"].search(domain, order='score desc', limit=limit * len(su.section_id.section_user_ids))
            users.append({
                "su": su,
                "nbr": min(su.maximum_user_leads - su.leads_count, limit),
                "leads": leads
            })

        assigned = {}
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

            #lead convert for this user
            lead = user['leads'][0]
            assigned[lead] = True
            if dry:
                values = {'lead_id': lead.id, 'section_id': user['su'].section_id.id, 'user_id': user['su'].user_id.id}
                self.env['leads.dry.run'].create(values)
            else:
                data = {'user_id': user['su'].user_id.id, 'assign_date': fields.Datetime.now()}
                lead.write(data)

                lead.convert_opportunity(None)
                self._cr.commit()

            user['nbr'] -= 1
            if not user['nbr']:
                del users[i]

    # ids is needed when the button is used to start the function,
    # the default [] is needed for the function to be usable by the cron
    @api.model
    def _assign_leads(self, dry=False):
        # Emptying the table
        self._cr.execute("""
                TRUNCATE TABLE leads_dry_run;
            """)

        salesteams_fields = ['score_section_domain',
                             'assigned_leads',
                             'capacity',
                             'name'
                             ]
        all_salesteams = self.search_read(fields=salesteams_fields, domain=[('score_section_domain', '!=', False)])
        # casting the list into a dict to ease the access afterwards

        all_section_users = self.env['section.user'].search([('running', '=', True)])

        self.assign_leads_to_salesteams(all_salesteams, dry=dry)
        self.assign_leads_to_salesmen(all_section_users, dry=dry)


class section_user(models.Model):
    _name = 'section.user'

    @api.one
    def _count_leads(self):
        if self.id:
            limit_date = datetime.datetime.now() - datetime.timedelta(days=30)
            domain = [('user_id', '=', self.user_id.id),
                      ('section_id', '=', self.section_id.id),
                      ('assign_date', '>', limit_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
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
    @api.constrains('section_user_domain')
    def _assert_valid_domain(self):
        try:
            domain = safe_eval(self.section_user_domain or '[]', evaluation_context)
            self.env['crm.lead'].search(domain)
        except Exception:
            raise Warning('The domain is incorrectly formatted')

    section_id = fields.Many2one('crm.case.section', string='SaleTeam', required=True)
    user_id = fields.Many2one('res.users', string='Saleman', required=True)
    name = fields.Char(related='user_id.partner_id.display_name')
    running = fields.Boolean(string='Running', default=True)
    section_user_domain = fields.Char('Domain')
    maximum_user_leads = fields.Integer('Leads Per Month')
    leads_count = fields.Integer('Assigned Leads', compute='_count_leads', help='Assigned Leads this last month')
    percentage_leads = fields.Float(compute='_get_percentage', string='Percentage leads')

    @api.one
    def toggle_active(self):
        self.running = not self.running
