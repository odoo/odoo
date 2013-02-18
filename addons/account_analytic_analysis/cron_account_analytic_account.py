#!/usr/bin/env python
from mako.template import Template
import time
import datetime
from dateutil.relativedelta import relativedelta

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from openerp import tools
from openerp.osv import osv

MAKO_TEMPLATE = u"""Hello ${user.name},

Here is a list of contracts that have to be renewed for two
possible reasons:
  - the end of contract date is passed
  - the customer consumed more hours than expected

Can you contact the customer in order to sell a new or renew its contract.
The contract has been set with a pending state, can you update the status
of the analytic account following this rule:
  - Set Done: if the customer does not want to renew
  - Set Open: if the customer purchased an extra contract

Here is the list of contracts to renew:
% for partner, accounts in partners.iteritems():
  * ${partner.name}
  % for account in accounts:
    - Name: ${account.name}
      % if account.quantity_max != 0.0:
      - Quantity: ${account.quantity}/${account.quantity_max} hours
      % endif
      - Dates: ${account.date_start} to ${account.date and account.date or '???'}
      - Contacts:
        ${account.partner_id.name}, ${account.partner_id.phone or ''}, ${account.partner_id.email or ''}

  % endfor
% endfor

You can use the report in the menu: Sales > Invoicing > Overdue Accounts

Regards,

--
OpenERP
"""

class analytic_account(osv.osv):
    _inherit = 'account.analytic.account'

    def cron_account_analytic_account(self, cr, uid, context=None):
        domain = [
            ('name', 'not ilike', 'maintenance'),
            ('partner_id', '!=', False),
            ('user_id', '!=', False),
            ('user_id.email', '!=', False),
            ('state', 'in', ('draft', 'open')),
            '|', ('date',  '<', time.strftime('%Y-%m-%d')), ('date', '=', False),
        ]

        account_ids = self.search(cr, uid, domain, context=context, order='name asc')
        accounts = self.browse(cr, uid, account_ids, context=context)

        users = dict()
        for account in accounts:
            users.setdefault(account.user_id, dict()).setdefault(account.partner_id, []).append(account)

            account.write({'state' : 'pending'}, context=context)

        for user, data in users.iteritems():
            subject = '[OPENERP] Reporting: Analytic Accounts'
            body = Template(MAKO_TEMPLATE).render_unicode(user=user, partners=data)
            tools.email_send('noreply@openerp.com', [user.email, ], subject, body)

        return True


    def cron_create_invoice(self, cr, uid, context=None):
        res = []
        inv_obj = self.pool.get('account.invoice')
        journal_obj = self.pool.get('account.journal')
        inv_lines = []
        
        contract_ids = self.search(cr, uid, [('next_date','<=',time.strftime("%Y-%m-%d")), ('state','=', 'open'), ('recurring_invoices','=', True)], context=context, order='name asc')
        print "\n000000000000 ids 0000000000000>",contract_ids
        
        a = self.pool.get('hr.timesheet.invoice.create.final').do_create(cr, uid, contract_ids, context=None)
        print"\n\n====================================================>",a
        contracts = self.browse(cr, uid, contract_ids, context=context)
        for contract in contracts:
#            journal_ids = journal_obj.search(cr, uid, [('type', '=','sale'),('company_id', '=', contract.company_id.id)], limit=1)
#            if not journal_ids:
#                raise osv.except_osv(_('Error!'),
#                    _('Define sale journal for this company: "%s" (id:%d).') % (contract.company_id.name, contract.company_id.id))
#            inv_data = {}
#            inv_data = {
#               'name': contract.name,
#               'reference': contract.name,
#               'account_id': contract.partner_id.property_account_receivable.id or contract.partner_id.property_account_receivable or False,
#               'type': 'in_invoice',
#               'partner_id': contract.partner_id.id,
#               'currency_id': contract.partner_id.property_product_pricelist.id,
#               'journal_id': len(journal_ids) and journal_ids[0] or False,
#               'invoice_line': [(6, 0, inv_lines)],
#               'date_invoice': contract.next_date,
#               'origin': contract.name,
#               'company_id': contract.company_id.id,
#               'contract_id': contract.id,
#            }
#            inv_id = inv_obj.create(cr, uid, inv_data, context=context)
#            inv_obj.button_compute(cr, uid, [inv_id], context=context, set_total=True)
            next_date = datetime.datetime.strptime(contract.next_date, "%Y-%m-%d")
            interval = contract.interval
            print"STRAT...................."
#            # compute the invoice
#            res.append(inv_id)        

            if contract.rrule_type == 'monthly':
                new_date = next_date+relativedelta(months=+interval)
            if contract.rrule_type == 'daily':
                new_date = next_date+relativedelta(days=+interval)
            if contract.rrule_type == 'weekly':
                new_date = next_date+relativedelta(weeks=+interval)

            print"==========res=============>",contract.next_date,contract.interval,contract.rrule_type,new_date
            # Link this new invoice to related contract
            contract.write({'next_date':new_date}, context=context)
        print"\n\n========11111==res=========FINISH.====>",res 
        return True

analytic_account()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
