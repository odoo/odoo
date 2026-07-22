from contextlib import contextmanager
from unittest.mock import patch

from zeep.plugins import HistoryPlugin

from odoo.tools import zeep

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_ge_edi.tests import stub_responses
from odoo.addons.l10n_ge_edi.tests.soap_transport_stub import SoapTransportStub
from odoo.addons.l10n_ge_edi.tools import rsge_client

RSGE_USER_ID = 783


class TestL10nGeEdiCommon(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country("ge")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.partner_id.write({"vat": "206322102", "l10n_ge_edi_un_id": "731937"})
        cls.tax_18 = cls.env["account.chart.template"].with_company(cls.company).ref("ge_vat_sale_18")
        cls.partner_ge = cls.env["res.partner"].create({
            "name": "GE Customer",
            "country_id": cls.env.ref("base.ge").id,
            "vat": "12345678910",
        })

        # a stored compute, so the handshake has to be forced here or it fires inside the first
        # test that reads it
        with cls._patch_rsge(chek=stub_responses.chek(user_id=RSGE_USER_ID)):
            cls.company.sudo().write({"l10n_ge_edi_su": "test_user:206322102", "l10n_ge_edi_sp": "password"})
            cls.rsge_user_id = cls.company.sudo().l10n_ge_edi_user_id

    @classmethod
    @contextmanager
    def _patch_rsge(cls, **responses):
        """Route RS.ge's SOAP calls to a stub answering `responses`, keyed by operation name."""
        transport = SoapTransportStub(**responses)
        client = zeep.Client(rsge_client.NTOSSERVICE_WSDL_URL, transport=transport)
        # the list calls need their own client, since their diffgram is recovered from the plugin
        history = HistoryPlugin()
        diffgram_client = zeep.Client(rsge_client.NTOSSERVICE_WSDL_URL, transport=transport, plugins=[history])
        with (
            patch.object(rsge_client, "_get_wsdl_client", lambda wsdl_url=None: client),
            patch.object(
                rsge_client,
                "_get_diffgram_client",
                lambda wsdl_url=None: (diffgram_client, history),
            ),
        ):
            yield transport

    def _stub_rsge(self, **responses):
        """Answer every RS.ge SOAP call from `responses` for the rest of this test."""
        return self.enterContext(self._patch_rsge(**responses))
