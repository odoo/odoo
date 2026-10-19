from lxml.html.clean import Cleaner

from odoo.tests.common import TransactionCase


class TestLxml(TransactionCase):

    def test_aria_preserved(self):
        """
        Ensures that the HTML Cleaner preserves ARIA attributes.
        """
        cleaner = Cleaner()
        html_input = """<div role="alert" aria-live="assertive">Error message</div>"""

        self.assertEqual(cleaner.clean_html(html_input), """<div role="alert" aria-live="assertive">Error message</div>""")
