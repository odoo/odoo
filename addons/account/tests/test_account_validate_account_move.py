from openerp.addons.mail.tests.common import TestMail

class TestAccountValidateAccount(TestMail):

    def setUp(self):
        super(TestAccountValidateAccount, self).setUp()

    def test_account_validate_account(self):
        account_move_line = self.env['account.move.line']
        account_cash = self.env['account.account'].search([('user_type.type', '=', 'liquidity')], limit=1)
        journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        
        # create move
        move = self.env['account.move'].create({'name': '/',
            'ref':'2011010',
            'journal_id': journal.id,
            'state':'draft',
        })
        
        # create move line
        account_move_line.create({'account_id': account_cash.id,
            'name': 'Basic Computer',
            'move_id': move.id,
        })
            
        # create another move line
        account_move_line.create({'account_id': account_cash.id,
            'name': 'Basic Computer',
            'move_id': move.id,
        })
    
        # check that Initially account move state is "Draft"
        self.assertTrue((move.state == 'draft'), "Initially account move state is Draft")

        # validate this account move by using the 'Post Journal Entries' wizard
        validate_account_move = self.env['validate.account.move'].create({'journal_ids':[(6, 0, [journal.id])]})
                
        #click on validate Button
        validate_account_move.validate_move();

        #check that the move state is now "Posted"
        self.assertTrue((move.state == 'posted'), "Initially account move state is Posted")
