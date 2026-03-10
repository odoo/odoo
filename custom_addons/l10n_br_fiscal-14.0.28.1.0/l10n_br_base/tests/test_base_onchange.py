# @ 2017 Akretion - www.akretion.com.br -
#   Clément Mombereau <clement.mombereau@akretion.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import SavepointCase


class L10nBrBaseOnchangeTest(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_01 = (
            cls.env["res.company"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Company Test 1",
                    "cnpj_cpf": "02.960.895/0001-31",
                    "city_id": cls.env.ref("l10n_br_base.city_3205002").id,
                    "zip": "29161-695",
                }
            )
        )

        cls.bank_01 = cls.env["res.bank"].create(
            {"name": "Bank Test 1", "zip": "29161-695"}
        )

        cls.partner_01 = (
            cls.env["res.partner"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Partner Test 01",
                    "zip": "29161-695",
                    "city_id": cls.env.ref("l10n_br_base.city_3205002").id,
                }
            )
        )

    def test_onchange(self):
        """
        Call all the onchange methods in l10n_br_base
        """
        self.company_01._onchange_cnpj_cpf()
        self.company_01._onchange_city_id()
        self.company_01._onchange_zip()
        self.company_01._onchange_state()
        # TODO: O metodo tanto no res.partner quanto no res.company chamam
        #  _onchange_state e aqui também deveria, porém por algum motivo
        #  ainda desconhecido se o metodo estiver com o mesmo nome não é
        #  chamado, por isso existe outro metodo com o final _id
        self.company_01._onchange_state_id()

        self.partner_01._onchange_cnpj_cpf()
        self.partner_01._onchange_city_id()
        self.partner_01._onchange_zip()
        self.partner_01._onchange_state()
        self.partner_01._onchange_state_id()

    def test_inverse_fields(self):
        self.company_01.inscr_mun = "692015742119"
        self.assertEqual(
            self.company_01.partner_id.inscr_mun,
            "692015742119",
            "The inverse function to field inscr_mun failed.",
        )
        self.company_01.suframa = "1234"
        self.assertEqual(
            self.company_01.partner_id.suframa,
            "1234",
            "The inverse function to field suframa failed.",
        )

    def test_display_address(self):
        partner = self.env.ref("l10n_br_base.res_partner_akretion")
        partner._onchange_city_id()
        display_address = partner._display_address()
        self.assertEqual(
            display_address,
            "Akretion Sao Paulo\n"
            "Avenida Paulista, 807 CJ 2315\nCentro"
            "\n01311-915 - São Paulo-SP\nBrazil",
            "The function _display_address failed.",
        )

    def test_display_address_parent_id(self):
        partner = self.env.ref("l10n_br_base.res_partner_address_ak2")
        partner._onchange_city_id()
        display_address = partner._display_address()
        self.assertEqual(
            display_address,
            "Akretion Rio de Janeiro\n"
            "Rua Acre, 47 sala 1310\nCentro"
            "\n20081-000 - Rio de Janeiro-RJ\nBrazil",
            "The function _display_address with parent_id failed.",
        )

    def test_other_country_display_address(self):
        partner = self.env.ref("l10n_br_base.res_partner_exterior")
        display_address = partner._display_address()
        self.assertEqual(
            display_address,
            "Cliente Exterior\n3404  Edgewood"
            " Road\n\nJonesboro"
            " AR 72401\nUnited States",
            "The function _display_address for other country failed.",
        )

    def test_display_address_without_company(self):
        partner = self.env.ref("l10n_br_base.res_partner_akretion")
        partner._onchange_city_id()
        display_address = partner._display_address(without_company=True)
        self.assertEqual(
            display_address,
            "Avenida Paulista, 807 CJ 2315\nCentro"
            "\n01311-915 - São Paulo-SP\nBrazil",
            "The function _display_address with parameter" " without_company failed.",
        )
