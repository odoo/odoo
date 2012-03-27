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
        ${account.partner_id.name}, ${account.partner_id.phone}, ${account.partner_id.email}

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
            ('user_id.user_email', '!=', False),
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
            tools.email_send('noreply@openerp.com', [user.user_email, ], subject, body)

        return True

analytic_account()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
