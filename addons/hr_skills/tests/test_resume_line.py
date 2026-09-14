from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResumeLineSiteName(TransactionCase):
    """The name guessed from an external URL is the site, not whatever precedes
    the last dot of the whole URL."""

    def test_the_site_is_read_from_the_host(self):
        line = self.env["hr.resume.line"]
        for url, expected in (
            ("https://www.udemy.com/course/python", "Udemy"),
            ("https://docs.python.org/3/", "Python"),
            ("coursera.org", "Coursera"),
            ("http://example.com/a.b.c", "Example"),
            ("localhost:8069", "Localhost"),
            ("", False),
        ):
            self.assertEqual(line._site_name(url), expected, url)

    def test_the_stored_url_is_a_web_address(self):
        employee = self.env["hr.employee"].create({"name": "Linked"})
        line = self.env["hr.resume.line"].create(
            {
                "employee_id": employee.id,
                "name": "Course",
                "external_url": " coursera.org ",
            }
        )
        self.assertEqual(line.external_url, "http://coursera.org")
        line.external_url = "javascript:alert(document.domain)"
        self.assertTrue(line.external_url.startswith("http://"))
        line.external_url = "https://www.edx.org/x"
        self.assertEqual(line.external_url, "https://www.edx.org/x")

    def test_the_onchange_fills_only_an_empty_name(self):
        employee = self.env["hr.employee"].create({"name": "Named"})
        line = self.env["hr.resume.line"].new(
            {"employee_id": employee.id, "external_url": "https://www.edx.org/x.y"}
        )
        line._onchange_external_url()
        self.assertEqual(line.name, "Edx")
        line.name = "Kept"
        line.external_url = "https://other.example/z"
        line._onchange_external_url()
        self.assertEqual(line.name, "Kept")
