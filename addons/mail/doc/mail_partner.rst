What is shown
==============
 - for every module which are related to partner show apporopriate message in the partner view like opportunities, sale orders and invoices.


How it is done
===============
 - _inherit = 'mail.thread'
 
 - Override def message_load_ids(self, cr, uid, ids, limit=100, offset=0, domain=[], ascent=False, root_ids=[], context=None) search by the partner
