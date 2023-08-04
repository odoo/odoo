from markupsafe import Markup

from odoo.tests import TransactionCase


class TestH2H(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.m = cls.env['test_new_api.html2html'].create({'h1': '<span><i foo="">em</i>phasi<tail>s</s></span>'})

    def test_sanitization(self):
        """custom attribute remains because stripping is disabled, custom element
        gets stripped (but not killed, content is kept)
        """
        self.assertEqual(self.m.h1, '<span><i foo="">em</i>phasis</span>')

    def test_copying(self):
        "related fields / direct copies should be identical"
        # related works because the sanitize attributes are copied over
        self.assertEqual(self.m.h2, '<span><i foo="">em</i>phasis</span>')
        self.assertEqual(self.m.h3, '<span><i foo="">em</i>phasis</span>')

    def test_compute(self):
        "bypasses sanitization and thus normalization as well (should it?), but not when set"
        self.assertEqual(self.m.h4, '<span><i foo="">em</i>phasis</span>whop whop')
        self.m.h4 = '<div foo="42">x</div>'
        self.assertEqual(self.m.h4, 'x')

    def test_unsanitized(self):
        source = Markup('<span><i foo="">em</i>phasi<tail>s</s></span>')
        m = self.env['test_new_api.html2html'].create({'h1': source})
        self.assertEqual(m.h1, source)
        self.assertEqual(m.h2, source)
        self.assertEqual(m.h3, source)
