
from openerp.osv import osv, fields


class project_issue(osv.Model):
    _inherit = 'project.issue'

    _columns = {
        'lead_id': fields.many2one('crm.lead', ondelete='set null', string="Related lead"),
    }

    _defaults = {

    }