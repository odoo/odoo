from openerp.osv import osv, fields

class job_post(osv.osv):
    _inherit = "hr.job"
    _columns = {
        'post_date': fields.date('Post Date'),
    }
