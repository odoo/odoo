import tools
from openerp.tests import common

class myLead(orm.Model):

    _name = name('base_action_rule.myLead')

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner', ondelete='set null',
            select=True, help="Linked partner (optional). Usually created when converting the lead."),
        'id': fields.integer('ID', readonly=True),
        'name': fields.char('Subject', size=64, required=True, select=1),
        'active': fields.boolean('Active', required=False),
        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),
        'email_from': fields.char('Email', size=128, help="Email address of the contact", select=1),
        'section_id': fields.many2one('crm.case.section', 'Sales Team', \
                        select=True, help='When sending mails, the default email address is taken from the sales team.'),
        'create_date': fields.datetime('Creation Date' , readonly=True),
        'email_cc': fields.text('Global CC', size=252 , help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'description': fields.text('Notes'),
        'write_date': fields.datetime('Update Date' , readonly=True),
        'categ_ids': fields.many2many('crm.case.categ', 'crm_lead_category_rel', 'lead_id', 'category_id', 'Categories', \
            domain="['|',('section_id','=',section_id),('section_id','=',False), ('object_id.model', '=', 'crm.lead')]"),
        'type_id': fields.many2one('crm.case.resource.type', 'Campaign', \
            domain="['|',('section_id','=',section_id),('section_id','=',False)]", help="From which campaign (seminar, marketing campaign, mass mailing, ...) did this contact come from?"),
        'channel_id': fields.many2one('crm.case.channel', 'Channel', help="Communication channel (mail, direct, phone, ...)"),
        'contact_name': fields.char('Contact Name', size=64),
        'partner_name': fields.char("Customer Name", size=64,help='The name of the future partner company that will be created while converting the lead into opportunity', select=1),
        'opt_out': fields.boolean('Opt-Out', oldname='optout', help="If opt-out is checked, this contact has refused to receive emails or unsubscribed to a campaign."),
        'type':fields.selection([ ('lead','Lead'), ('opportunity','Opportunity'), ],'Type', help="Type is used to separate Leads and Opportunities"),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority', select=True),
        'date_closed': fields.datetime('Closed', readonly=True),
        'stage_id': fields.many2one('crm.case.stage', 'Stage',
                        domain="['&', ('fold', '=', False), '&', '|', ('section_ids', '=', section_id), ('case_default', '=', True), '|', ('type', '=', type), ('type', '=', 'both')]"),
        'user_id': fields.many2one('res.users', 'Salesperson'),
        'referred': fields.char('Referred By', size=64),
        'date_open': fields.datetime('Opened', readonly=True),
        'day_open': fields.function(_compute_day, string='Days to Open', \
                                multi='day_open', type="float", store=True),
        'day_close': fields.function(_compute_day, string='Days to Close', \
                                multi='day_close', type="float", store=True),
        'state': fields.related('stage_id', 'state', type="selection", store=True,
                selection=crm.AVAILABLE_STATES, string="Status", readonly=True,
                help='The Status is set to \'Draft\', when a case is created. If the case is in progress the Status is set to \'Open\'. When the case is over, the Status is set to \'Done\'. If the case needs to be reviewed then the Status is  set to \'Pending\'.'),

        # Only used for type opportunity
        'probability': fields.float('Success Rate (%)',group_operator="avg"),
        'planned_revenue': fields.float('Expected Revenue'),
        'ref': fields.reference('Reference', selection=crm._links_get, size=128),
        'ref2': fields.reference('Reference 2', selection=crm._links_get, size=128),
        'phone': fields.char("Phone", size=64),
        'date_deadline': fields.date('Expected Closing', help="Estimate of the date on which the opportunity will be won."),
        'date_action': fields.date('Next Action Date', select=True),
        'title_action': fields.char('Next Action', size=64),
        'color': fields.integer('Color Index'),
        'partner_address_name': fields.related('partner_id', 'name', type='char', string='Partner Contact Name', readonly=True),
        'partner_address_email': fields.related('partner_id', 'email', type='char', string='Partner Contact Email', readonly=True),
        'company_currency': fields.related('company_id', 'currency_id', type='many2one', string='Currency', readonly=True, relation="res.currency"),
        'user_email': fields.related('user_id', 'email', type='char', string='User Email', readonly=True),
        'user_login': fields.related('user_id', 'login', type='char', string='User Login', readonly=True),

        # Fields for address, due to separation from crm and res.partner
        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state_id': fields.many2one("res.country.state", 'State'),
        'country_id': fields.many2one('res.country', 'Country'),
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'mobile': fields.char('Mobile', size=64),
        'function': fields.char('Function', size=128),
        'title': fields.many2one('res.partner.title', 'Title'),
        'company_id': fields.many2one('res.company', 'Company', select=1),
        'payment_mode': fields.many2one('crm.payment.mode', 'Payment Mode', \
                            domain="[('section_id','=',section_id)]"),
        'planned_cost': fields.float('Planned Costs'),
    }

    _defaults = {
        'active': 1,
        'type': 'lead',
        'user_id': lambda s, cr, uid, c: s._get_default_user(cr, uid, c),
        'email_from': lambda s, cr, uid, c: s._get_default_email(cr, uid, c),
        'stage_id': lambda s, cr, uid, c: s._get_default_stage_id(cr, uid, c),
        'section_id': lambda s, cr, uid, c: s._get_default_section_id(cr, uid, c),
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.lead', context=c),
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
        'color': 0,
    }


class base_action_rule_test(common.TransactionCase):

    def setUp(self):
        """*****setUp*****"""
        super(base_action_rule_test, self).setUp()
        cr, uid = self.cr, self.uid

        """********TeamCreation******"""
        self.team_pool = self.pool.get('crm.case.section')
        self.team_1_id = self.team_pool.create(cr, uid, {
            
            }, context=None)

        self.myLead_pool = self.pool.get('base_action_rule.myLead')
        self.new_myLead_id = self.myLead_pool.create(cr, uid, {
            'name' : "my_first_lead",
            'section_id' : 
            }, context=None)
