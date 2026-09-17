import random
import time
from datetime import timedelta
from logging import getLogger

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tests.common import warmup

from odoo.addons.calendar.tests.booking.common import AppointmentCommon

_logger = getLogger(__name__)


class AppointmentPerformanceCase(AppointmentCommon):
    def setUp(self):
        super().setUp()
        # patch registry to simulate a ready environment
        self.patch(self.env.registry, "ready", True)
        # we don't use mock_mail_gateway thus want to mock smtp to test the stack
        self._mock_smtplib_connection()


class AppointmentUIPerformanceCase(AppointmentPerformanceCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        shipped_type_ids = (
            cls.env["ir.model.data"]
            .search([("model", "=", "appointment.type")])
            .mapped("res_id")
        )
        cls.env["appointment.type"].browse(shipped_type_ids).exists().active = False
        cls._website_renders_the_page = "website" in cls.env

        # tweak in case website is installed
        if "website" in cls.env and "channel_id" in cls.env["website"]:
            # if website_livechat is installed, disable it
            cls.env["website"].search([]).channel_id = False

            # remove menu containing a slug url (only website_helpdesk normally), to
            # avoid the menu cache being disabled, which would increase sql queries.
            cls.env["website.menu"].search(
                [
                    ("url", "=like", "/%/%-%"),
                ]
            ).unlink()


@tagged("appointment_performance", "post_install", "-at_install")
class OnlineAppointmentPerformance(AppointmentUIPerformanceCase):
    def setUp(self):
        super().setUp()
        # Setup already some meetings for the staff user of appointment type
        self._create_meetings(
            self.staff_user_bxls,
            [
                (
                    self.reference_monday + timedelta(days=1),  # 3 hours first Tuesday
                    self.reference_monday + timedelta(days=1, hours=3),
                    False,
                ),
                (
                    self.reference_monday
                    + timedelta(days=7),  # next Monday: one full day
                    self.reference_monday + timedelta(days=7, hours=1),
                    True,
                ),
            ],
        )

        # When website_sale is installed, rendering the web page
        # fetches the user's current sales order leading to a loading
        # of available pricelists for that user.
        # A fallback mechanism is in place in pricelists (see `_get_partner_pricelist_multi`)
        # causing the queryCount to go up when a first pricelist is not found.
        if "product.pricelist" in self.env:
            self.env["product.pricelist"].search([]).write({"active": False})

        # Flush everything, notably tracking values, as it may impact performances
        self.flush_tracking()

    @warmup
    def test_appointment_invitation_page_anonymous(self):
        """Anonymous access of invitation page"""
        random.seed(1871)  # fix shuffle in _slots_add_users_availability
        invitation = self.env["appointment.invite"].create(
            {
                "short_code": "spock",
                "appointment_type_ids": self.apt_type_bxls_2days.ids,
            }
        )

        self.authenticate(None, None)
        t0 = time.time()
        with freeze_time(self.reference_now):
            with self.assertQueryCount(
                default=30 if self._website_renders_the_page else 27
            ):
                response = self._test_url_open(invitation.redirect_url)
        self.assertEqual(response.status_code, 200)
        t1 = time.time()

        _logger.info("Browsed %s, time %.3f", invitation.redirect_url, t1 - t0)

    @warmup
    def test_appointment_type_page_website_authenticated(self):
        """Authenticated access of Appointment type page"""
        random.seed(1871)  # fix shuffle in _slots_add_users_availability
        self.apt_type_bxls_2days.is_published = True

        self.authenticate("staff_user_aust", "staff_user_aust")
        t0 = time.time()
        with freeze_time(self.reference_now):
            with self.assertQueryCount(31 if self._website_renders_the_page else 27):
                response = self._test_url_open(
                    "/appointment/%i" % self.apt_type_bxls_2days.id
                )
        self.assertEqual(response.status_code, 200)
        t1 = time.time()

        _logger.info(
            "Browsed /appointment/%i, time %.3f", self.apt_type_bxls_2days.id, t1 - t0
        )
