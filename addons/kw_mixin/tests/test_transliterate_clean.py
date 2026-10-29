from odoo.tests.common import TransactionCase


class TestDatetimeExtract(TransactionCase):

    def test_100_clean_up_mixin(self):
        self.assertEqual(
            self.env['kw.clean.up.mixin'].transliterate_visual('АВС'), 'ABC')
        self.assertEqual(
            self.env['kw.clean.up.mixin'].transliterate_visual(123), 123)

        self.assertEqual(
            self.env['kw.clean.up.mixin'].transliterate('АВС'), 'AVS')
        self.assertEqual(
            self.env['kw.clean.up.mixin'].transliterate(123), 123)

        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_cleanup_string('(ABC)'), 'ABC')
        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_cleanup_string(123), '')

        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_model_name(
                '(АВС-sd)'), 'ABC-SD')
        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_model_name(123), 123)

        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_alpha_digit(
                '(ABC-123)'), 'ABC123')
        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_alpha_digit(123), 123)

        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_alpha_only(
                '(ABC-123)'), 'ABC')
        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_alpha_only(123), 123)

        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_ukr_alpha_only(
                '(ЙФЯ-123)гоь'), 'ЙФЯгоь')
        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_ukr_alpha_only(123), 123)

        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_ukr_alpha_whitespace(
                '(ЙФЯ-123) гоь'), 'ЙФЯ гоь')
        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_ukr_alpha_whitespace(
                123), 123)

        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_cyr_alpha_whitespace(
                '(ЙФЯ-123) гоь'), 'ЙФЯ гоь')
        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_cyr_alpha_whitespace(
                123), 123)

        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_digit_only(
                '(ЙФЯ-123) гоь'), '123')
        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_digit_only(
                123), 123)

        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_index_model_name(
                '(LG-123) xxx'), '123XXX')
        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_index_model_name(
                123), 123)

        self.assertEqual(
            self.env['kw.clean.up.mixin'].kw_clean_remove_html_tags(
                '<a href="http://www.com">www</a>'), 'www')
