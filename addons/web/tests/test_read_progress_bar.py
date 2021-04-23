from odoo.tests.common import TransactionCase, tagged


@tagged('read_progress_bar')
class TestReadProgressBar(TransactionCase):

    def test_read_progress_bar_m2m(self):
        """ Test that read_progress_bar works with m2m field grouping """
        progressbar = {
            'field': 'type',
            'colors': {
                'contact': 'success', 'private': 'danger', 'other': 'muted',
            }
        }
        result = self.env['res.partner'].read_progress_bar([], 'category_id', progressbar)
        # check that it works when grouping by m2m field
        self.assertTrue(result)
        # check the null group
        self.assertIn(False, result)
