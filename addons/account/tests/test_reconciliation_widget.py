import logging
import odoo.tests
import time
import requests

_logger = logging.getLogger(__name__)


@odoo.tests.tagged('post_install', '-at_install')
@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUi(odoo.tests.HttpCase):

    def test_01_admin_bank_statement_reconciliation(self):
        bank_stmt_name = 'BNK/%s/0001' % time.strftime('%Y')
        bank_stmt_line = self.env['account.bank.statement'].search([('name', '=', bank_stmt_name)]).mapped('line_ids')
        if not bank_stmt_line:
             _logger.exception('Could not find bank statement %s' % bank_stmt_name)

        # To be able to test reconciliation, admin user must have access to accounting features, so we give him the right group for that
        self.env.ref('base.user_admin').write({'groups_id': [(4, self.env.ref('account.group_account_user').id)]})
        
        payload = {'action':'bank_statement_reconciliation_view', 'statement_line_ids[]': bank_stmt_line.ids}
        prep = requests.models.PreparedRequest()
        prep.prepare_url(url="http://localhost/web#", params=payload)

        self.phantom_js(prep.url.replace('http://localhost','').replace('?','#'),
            "odoo.__DEBUG__.services['web_tour.tour'].run('bank_statement_reconciliation')",
            "odoo.__DEBUG__.services['web_tour.tour'].tours.bank_statement_reconciliation.ready", login="admin")
