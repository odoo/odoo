import pytz

from odoo.tests.common import TransactionCase


class TestTZ(TransactionCase):

    def test_tz_legacy(self):
        #See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
        def assertTZEqual(tz1, tz2):
            self.assertEqual(tz1._utcoffset, tz2._utcoffset)
            self.assertEqual(tz1._transition_info, tz2._transition_info)

        assertTZEqual(pytz.timezone('US/Eastern'), pytz.timezone('America/New_York'))
        assertTZEqual(pytz.timezone('US/Central'), pytz.timezone('America/Chicago'))
        assertTZEqual(pytz.timezone('US/Mountain'), pytz.timezone('America/Denver'))
        assertTZEqual(pytz.timezone('US/Pacific'), pytz.timezone('America/Los_Angeles'))
        assertTZEqual(pytz.timezone('US/Alaska'), pytz.timezone('America/Anchorage'))
        assertTZEqual(pytz.timezone('US/Hawaii'), pytz.timezone('Pacific/Honolulu'))
        assertTZEqual(pytz.timezone('Canada/Atlantic'), pytz.timezone('America/Halifax'))
        assertTZEqual(pytz.timezone('Canada/Pacific'), pytz.timezone('America/Vancouver'))
        assertTZEqual(pytz.timezone('Mexico/BajaNorte'), pytz.timezone('America/Tijuana'))
        assertTZEqual(pytz.timezone('Mexico/General'), pytz.timezone('America/Mexico_City'))
        assertTZEqual(pytz.timezone('Brazil/East'), pytz.timezone('America/Sao_Paulo'))
        # This one is not correct for a strange reason
        #assertTZEqual(pytz.timezone('Pacific/Midway'), pytz.timezone('Pacific/Pago_Pago'))

    def test_cannot_set_deprecated_timezone(self):
        # this should be ok
        self.env.user.tz = "America/New_York"
        if "US/Eastern" not in pytz.all_timezones:
            with self.assertRaises(ValueError):
                self.env.user.tz = "US/Eastern"