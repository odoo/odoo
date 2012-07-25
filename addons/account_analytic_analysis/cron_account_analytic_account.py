#!/usr/bin/env python
from osv import osv
from mako.template import Template
import time
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

import tools

MAKO_TEMPLATE = u"""Hello ${user.name},

Here is a list of contracts that have to be renewed for two
possible reasons:
  - the end date of the contract is passed
  - the customer consumed more hours than included in the contract

Can you contact the customer in order to sell a new or renew their contract.
The contract has been set with a pending state, please update its status
following this rule:
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
        % for address in account.partner_id.address:
        . ${address.name}, ${address.phone}, ${address.email}
        % endfor

  % endfor
% endfor

You can use the report in the menu: Sales > Invoicing > Contracts To Renew

Regards,

--
OpenERP
"""

class analytic_account(osv.osv):
    _inherit = 'account.analytic.account'

    def cron_account_analytic_account(self, cr, uid, context=None):
        domain = [
            ('partner_id', '!=', False),
            ('state', 'in', ('draft', 'open')),
            '|', ('date',  '<=', time.strftime('%Y-%m-%d')),
                 ('is_overdue_quantity', '=', True),
        ]
        users = {}
        account_ids = self.search(cr, uid, domain, context=context, order='name asc')
        accounts = self.browse(cr, uid, account_ids, context=context)
        for account in accounts:
            account.write({'state' : 'pending'})
            if account.user_id:
                users.setdefault(account.user_id, {}).setdefault(account.partner_id, []).append(account)

        mail_message = self.pool.get('mail.message')
        for user, data in users.iteritems():
            subject = '[OPENERP] Reporting: Analytic Accounts'
            body = Template(MAKO_TEMPLATE).render_unicode(user=user, partners=data)
            if user.user_email:
                mail_message.schedule_with_attach(cr, uid, 'noreply@openerp.com', [user.user_email],
                                                  subject, body)

        return True

analytic_account()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
