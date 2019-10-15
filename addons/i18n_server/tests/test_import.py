# -*- coding: utf-8 -*-

from odoo import tests, tools


@tests.tagged("post_install", "-at_install")
class TestImport(tests.HttpCase):
    def setUp(self):
        super().setUp()

        self.env["ir.config_parameter"].set_param(
            "i18n.default.server", "http://%s:%s" % (tests.HOST, tools.config['http_port'])
        )
        self.lang = self.env["res.lang"].create(
            {"name": "Klingon", "code": "tlh", "iso_code": "tlh"}
        )

    def test_download_lang(self):
        """
        Just make sure we have as many translation entries as we wanted.
        """
        self.env["i18n.pack"]._generate_pack(languages=self.lang)
        self.lang._install_language(remote=True)

        translations = self.env["ir.translation"].search([
            ("module", "=", "i18n_server"),
            ("type", "=", "code"),
            ("lang", "=", "tlh"),
            ("src", "=", "Language pack for modules: %s"),
        ])
        self.assertRecordValues(translations, [{"value": "Hol pack bobcho': %s"}])
