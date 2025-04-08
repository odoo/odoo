from odoo.tests import tagged
import logging

from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon

_logger = logging.getLogger(__name__)

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestReports(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_b.l10n_in_gst_treatment = 'regular'
        cls.partner_a.l10n_in_gst_treatment = 'composition'
        cls.partner_foreign.l10n_in_gst_treatment = 'overseas'

        cls.igst_sale_18 = cls.env['account.chart.template'].ref('igst_sale_18')

    def test_partner_details_change_with_invoice(self):
        invoice_b_2 = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_b,
            amounts=[250, 600],
            taxes=[self.igst_sale_18],
            post=True
        )

        # Place of Supply (pos) is same as of state of partner (for journal type sale)
        expected_pos_id = self.state_in_mh.id
        self.assertRecordValues(
            self.invoice_b,
            [{
                'state': 'draft',
                'l10n_in_gst_treatment': self.partner_b.l10n_in_gst_treatment,
                'l10n_in_state_id': expected_pos_id,
            }]
        )
        self.assertRecordValues(
            invoice_b_2,
            [{
                'state': 'posted',
                'l10n_in_gst_treatment': self.partner_b.l10n_in_gst_treatment,
                'l10n_in_state_id': expected_pos_id,
            }]
        )
        self.partner_b.write({
            'vat': False,
            'l10n_in_gst_treatment': 'unregistered',
            'state_id': self.state_in_hp,  # change state of partner
        })
        self.assertRecordValues(
            self.invoice_b,
            [{
                'state': 'draft',
                'l10n_in_gst_treatment': self.partner_b.l10n_in_gst_treatment,
                'l10n_in_state_id': expected_pos_id, # POS doesn't change unless the partner changes
            }]
        )
        self.assertRecordValues(
            invoice_b_2,
            [{ # check gst treatment and pos doesn't change on posted invoice
                'state': 'posted',
                'l10n_in_gst_treatment': 'regular',
            }]
        )

    def test_partner_change_with_invoice(self):
        in_invoice = self.init_invoice(
            move_type='in_invoice',
            partner=self.partner_b,
            amounts=[452, 58, 110],
            taxes=[self.igst_sale_18],
        )

        self.assertRecordValues(
            self.invoice_a,
            [{
                'state': 'draft',
                'l10n_in_gst_treatment': self.partner_a.l10n_in_gst_treatment,
                'l10n_in_state_id': self.state_in_gj.id,
            }]
        )
        self.invoice_a.partner_id = self.partner_foreign
        self.assertRecordValues(
            self.invoice_a,
            [{
                'state': 'draft',
                'l10n_in_gst_treatment': self.partner_foreign.l10n_in_gst_treatment,
                'l10n_in_state_id': self.env.ref("l10n_in.state_in_oc").id,
            }]
        )
        self.assertRecordValues(
            in_invoice,
            [{
                'state': 'draft',
                'l10n_in_gst_treatment': self.partner_b.l10n_in_gst_treatment,
                'l10n_in_state_id': self.env.company.state_id.id,
            }]
        )

    def test_place_of_supply(self):
        child_partner = self.env['res.partner'].create({
            'name': "Child Contact",
            'type': "delivery",
            'parent_id': self.partner_a.id,
            'state_id': self.state_in_hp.id
        })

        self.assertRecordValues(
            self.invoice_a,
            [{
                'partner_shipping_id': self.partner_a.id,
                'l10n_in_state_id': self.partner_a.state_id.id,
            }]
        )
        self.invoice_a.partner_shipping_id = child_partner
        self.assertRecordValues(
            self.invoice_a,
            [{
                'partner_shipping_id': child_partner.id,
                'l10n_in_state_id': child_partner.state_id.id,
            }]
        )
        self.invoice_a.partner_shipping_id = self.partner_b
        self.assertRecordValues(
            self.invoice_a,
            [{
                'l10n_in_state_id': self.partner_a.state_id.id,
            }]
        )
