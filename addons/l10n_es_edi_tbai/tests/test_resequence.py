from odoo.addons.l10n_es_edi_sii.tests import test_resequence


class TestResequenceTbai(test_resequence.TestResequenceSII):
    @classmethod
    def setUpClass(
        cls,
        chart_template_ref="l10n_es.account_chart_template_full",
        edi_format_ref="l10n_es_edi_sii.edi_es_sii",
    ):
        super().setUpClass(
            chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref
        )
