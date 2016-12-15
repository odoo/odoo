from openerp.tests import common


class TestDisplayAddress(common.TransactionCase):
    def test_display_address(self):
        """ _display_address() should not include empty lines when some data is missing """
        partner = self.env['res.partner'].create(
            {'name': 'Test partner',
             'street': 'Test street',
             'city': 'Test city'})
        self.assertNotIn('\n\n', partner._display_address(partner))
