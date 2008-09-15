# -*- encoding: utf-8 -*-
import wizard
import netsvc
import pooler

def _wo_check(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    current_auction=pool.get('auction.dates').browse(cr,uid,data['id'])
    v_lots=pool.get('auction.lots').search(cr,uid,[('auction_id','=',current_auction.id)])
    v_ids=pool.get('auction.lots').browse(cr,uid,v_lots)
    for ab in v_ids:
        if not ab.auction_id :
            raise wizard.except_wizard('Error!','No Lots belong to this Auction Date')
    return 'report'

class wizard_report(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result' : {'type': 'choice', 'next_state': _wo_check }
        },
        'report': {
            'actions': [],
            'result': {'type':'print', 'report':'auction.cat_flagy', 'state':'end'}
        }
    }
wizard_report('auction.catalog.flagey')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

