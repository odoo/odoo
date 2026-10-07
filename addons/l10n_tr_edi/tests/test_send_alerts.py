from odoo.tests import tagged

from odoo.addons.l10n_tr_edi.tests.test_xml_ubl_tr_common import TestUBLTRCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSendAlerts(TestUBLTRCommon):

    def test_no_provider_is_explained(self):
        self.env.company.l10n_tr_edi_provider = False
        invoice = self._generate_invoice(self.einvoice_partner)

        wizard = self.env['account.move.send.wizard'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'move_id': invoice.id,
        })

        # The GİB option is not offered without a provider: the wizard says why instead of staying silent.
        self.assertIn('l10n_tr_edi_no_provider', wizard.alerts)
