from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountValidateAccount(AccountingTestCase):

    def test_account_validate_account(self):
        account_move_line = self.env['account.move.line']
        account_cash = self.env['account.account'].search([('user_type_id.type', '=', 'liquidity')], limit=1)
        journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)

        company_id = self.env['res.users'].browse(self.env.uid).company_id.id

        # create move
        move = self.env['account.move'].create({'name': '/',
            'ref':'2011010',
            'journal_id': journal.id,
            'state':'draft',
            'company_id': company_id,
        })
        # create move line
        account_move_line.create({'account_id': account_cash.id,
            'name': 'Four Person Desk',
            'move_id': move.id,
        })

        # create another move line
        account_move_line.create({'account_id': account_cash.id,
            'name': 'Four Person Desk',
            'move_id': move.id,
        })

        # check that Initially account move state is "Draft"
        self.assertTrue((move.state == 'draft'), "Initially account move state is Draft")

        # validate this account move by using the 'Post Journal Entries' wizard
        validate_account_move = self.env['validate.account.move'].with_context(active_ids=move.id).create({})

        #click on validate Button
        validate_account_move.with_context({'active_ids': [move.id]}).validate_move()

        #check that the move state is now "Posted"
        self.assertTrue((move.state == 'posted'), "Initially account move state is Posted")
