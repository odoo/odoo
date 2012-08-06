from osv import fields, osv
import tools

class account_move_reconciliation(osv.osv):
    _inherit = 'account.move.reconciliation'
    _columns = {
                'followup_date': fields.date('Latest Follow-up'),
                'max_followup_id':fields.many2one('account_followup.followup.line',
                                    'Max Follow Up Level' )
    }
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_move_reconciliation')
        cr.execute("""
          CREATE or REPLACE VIEW account_move_reconciliation as (
                SELECT  p.id, p.id as partner_id, 
                MAX(p.last_reconciliation_date) as last_reconciliation_date,
                MAX(l.date) as latest_date, 
                COUNT(l.id)  as move_lines_count,
                MAX(p.partner_move_count) as partner_move_count,
                MAX(l.followup_date) as followup_date,
                MAX(l.followup_line_id) as max_followup_id
                FROM account_move_line as l INNER JOIN res_partner AS p ON (l.partner_id = p.id)
                GROUP by p.id
                )
        """)
account_move_reconciliation()