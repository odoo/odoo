from odoo.tests import tagged
from odoo.addons.l10n_jo_edi_pos.tests.jo_edi_pos_common import JoEdiPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nJoEdiPosTour(JoEdiPosCommon):

    def test_l10n_jo_edi_pos_tour(self):
        self.company.write({
            'l10n_jo_edi_pos_enabled': True,
            'l10n_jo_edi_pos_testing_mode': True,
            'l10n_jo_edi_demo_mode': True,
            'l10n_jo_edi_sequence_income_source': '12345',
            'l10n_jo_edi_secret_key': 'demo_secret_key',
            'l10n_jo_edi_client_identifier': 'demo_client_identifier',
            'l10n_jo_edi_taxpayer_type': 'income',
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "L10nJoEdiPosTour", login="pos_user",
        )
