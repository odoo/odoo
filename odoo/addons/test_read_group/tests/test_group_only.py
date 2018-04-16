from odoo.tests import common


class TestDatetimeOnly(common.TransactionCase):
    """ Test grouping date:only_INTERVAL1_..._INTERVALLAST
    """
    def setUp(self):
        super(TestDatetimeOnly, self).setUp()
        self.Model = self.env['test_read_group.on_datetime']

    def test_only_hour(self):
        self.Model.create({'datetime': '2000-12-18 12:01:02', 'value': 10})
        self.Model.create({'datetime': '2000-12-18 13:01:02', 'value': 20})

        self.Model.create({'datetime': '2000-12-19 12:01:02', 'value': 1})
        self.Model.create({'datetime': '2000-12-19 13:01:02', 'value': 2})

        gb = self.Model.read_group([], ['datetime', 'value'], ['datetime:only_hour'], lazy=False)

        self.assertSequenceEqual(sorted(gb, key=lambda r: r['datetime:only_hour'] or ''), [{
            '__count': 2,
            '__domain': [('datetime', '=', '12:00:00')],
            'datetime:only_hour': '12:00:00',
            'value': 11,
        }, {
            '__count': 2,
            '__domain': [('datetime', '=', '13:00:00')],
            'datetime:only_hour': '13:00:00',
            'value': 22,
        }])
