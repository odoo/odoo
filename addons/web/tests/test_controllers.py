from odoo.tests.common import get_db_name, HttpCase


class FirstTimeVisitorCase(HttpCase):
    def setUp(self):
        super().setUp()
        # Tests in this class are for `auth="none"` controllers, which we emulate
        # removing session_id cookie; this way it's like a 1st time visitor
        del self.opener.cookies["session_id"]

    def test_dbredirect(self):
        """Redirections to db-less requests work as expected."""
        # Test a db-redirection to download a barcode.
        # The barcode itself is not relevant. The important thing is that
        # `/report/barcode` is an `auth="public"` controller, which requires a DB but
        # not a login. Using `/web/dbredirect` should create a new `session_id` cookie
        # automatically which points to the chosen DB. We test that system works.
        response = self.url_open(
            "/web/dbredirect?db={}&redirect=%2Freport%2Fbarcode%2FQR%2Ftest%3Fheight%3D1%26width%3D1".format(
                get_db_name()
            )
        )
        self.assertTrue(response.ok)
        # The redirection took place as expected
        self.assertEqual(
            response.request.path_url, "/report/barcode/QR/test?height=1&width=1",
        )
