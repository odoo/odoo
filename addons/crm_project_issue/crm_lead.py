
from openerp.osv import osv, fields


class crm_lead(osv.Model):
    _inherit = 'crm.lead'

    _columns = {
        'project_issue_ids': fields.one2many('project.issue', 'lead_id', "Project Issues"),
    }
