from odoo.tests import common


class TestDateNumber(common.TransactionCase):
    """ Test grouping date:Nmonth and similar
    """
    def setUp(self):
        super(TestDateNumber, self).setUp()
        self.Model = self.env['test_read_group.on_date']

    def test_group_month(self):
        self.Model.create({'date': '2000-01-18', 'value': 1})
        self.Model.create({'date': '2000-02-19', 'value': 20})
        self.Model.create({'date': '2000-03-20', 'value': 300})


        gb = self.Model.read_group([], ['date', 'value'], ['date:2month'], lazy=False)

        self.assertSequenceEqual(sorted(gb, key=lambda r: r['date:2month'] or ''), [{
            '__count': 2,
            '__domain': ['&', ('date', '>=', '2000-01-01'), ('date', '<', '2000-03-01')],
            'date:2month': 'January 2000',
            'value': 21,
        }, {
            '__count': 1,
            '__domain': ['&', ('date', '>=', '2000-03-01'), ('date', '<', '2000-05-01')],
            'date:2month': 'March 2000',
            'value': 300,
        }])
