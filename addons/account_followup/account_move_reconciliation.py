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
                SELECT  move_line.partner_id as id, move_line.partner_id, 
                MAX(move_line.date) as latest_date,
                MAX(move_line.followup_date) as followup_date,
                MAX(move_line.followup_line_id) as max_followup_id,
                (select count(unreconcile.id) from account_move_line as unreconcile where unreconcile.reconcile_id is null and unreconcile.partner_id = move_line.partner_id) as unreconcile_count
                FROM account_move_line as move_line where move_line.state <> 'draft'
                GROUP by move_line.partner_id
                )
        """)
account_move_reconciliation()