from odoo.tests.common import TransactionCase
from xml.dom.minidom import parse
import os


class TestDataLoadSuccess(TransactionCase):

    """ Tests wether module was installed successfuly and all data is loaded
        Two sepcial cases need to be considered: empty DB and DB with existing chart of accounts
        For empty DB success means that all data is loaded, taxes and accounts are activated
        For DB with existing chart of accounts success means that tax tags are available, account types are available,
        fiscal postions are available, but without tax definitions
    """


    def test_accounts_load(self):
        # Verify that some accounts exist (either our or previous)
        self.assertEqual(len(self.env['account.account'].search([("name", "=", "Aineettomat oikeudet, poistot")])), 1,
                         'Fi accounts were not loaded')

    def test_account_types(self):
        # Verify that account types have been loaded
        self.assertEqual(len(self.env['account.account.type'].search([("name","=","Rakennukset omistetut")])),1,
                        'Problem in loading of account types')

    def test_taxes(self):

        # Verify that taxes are loaded, by checking one of the taxes
        self.assertEqual(len(self.env['account.tax'].search([("name","=","Purchase 14% EU Service2")])),1, 'FI taxes were not loaded')

        # Check tags
        self.assertEqual(len(self.env['account.account.tag'].search([("name", "=", "302-sales14")])), 1,
                         'FI taxes were not loaded')

    def test_fiscal_positions(self):
        # Verify that our fiscal position exist (use total count)
        self.assertEqual(len(self.env['account.fiscal.position'].search([])), 5,
                         'Problem in loading of fiscal positions')

        # Verify that if our taxes exist, also fiscal postition tax is set
        self.assertEqual(len(self.env['account.fiscal.position'].search([('name','=','EU (ei FI)')])[0].tax_ids),
                             18,"Problem in loadind fiscal position taxes")





