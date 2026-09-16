from datetime import timedelta

from lxml import etree

from odoo import Command, fields, models
from odoo.libs.documents import Document, extension_for, mimetype_for

from .preferred_classification import INVOICE_TYPES_HAVE_EXPENSE
from odoo.addons.exchange.tools import Verdict

XML_MIMETYPE = mimetype_for("xml")

NS_MYDATA = {"ns": "http://www.aade.gr/myDATA/invoice/v1.0"}

INBOX_DAYS = 90

VAT_CATEGORY_AMOUNT = {
    "1": 24.0,
    "2": 13.0,
    "3": 6.0,
    "4": 17.0,
    "5": 9.0,
    "6": 4.0,
    "7": 0.0,
    "8": 0.0,
}


def _find(element, name: str) -> str:
    return element.findtext(f".//ns:{name}", namespaces=NS_MYDATA)


ENDPOINTS = {
    "invoice": "SendInvoices",
    "classification": "SendExpensesClassification",
}

TEMPLATES = {
    "invoice": "l10n_gr_edi.mydata_invoice",
    "classification": "l10n_gr_edi.mydata_expense_classification",
}


class ExchangeProtocolMydata(models.AbstractModel):
    _name = "exchange.protocol.mydata"
    _inherit = ["exchange.protocol"]
    _description = "myDATA (AADE)"
    _protocol_code = "mydata"
    _protocol_label = "myDATA"
    _document_kinds = {
        "invoice": "Invoice",
        "classification": "Expense Classification",
    }
    # myDATA takes a document list in one call and answers per index. The cap is
    # ours, not the authority's: a rejected batch is retried whole, so a smaller
    # one costs less to redo.
    _batch_size = 50

    # PROTOCOL METHODS

    def _get_message_errors(self, transmission) -> list[str]:
        error = transmission.subject_id._l10n_gr_edi_get_pre_error_string()
        return [error] if error else []

    def _prepare_message(self, transmission):
        move = transmission.subject_id
        kind = self._get_kind(transmission)
        entry = self._get_entries(move, kind)[0]
        return Document(
            move._l10n_gr_edi_generate_xml_content(
                TEMPLATES[kind], {"invoice_values_list": [entry]}
            ),
            mimetype=XML_MIMETYPE,
            name=self._get_filename(move),
        )

    def _send_batch(self, transmissions) -> dict[int, Verdict]:
        kind = self._get_kind(transmissions[:1])
        moves = self.env["account.move"].browse(
            [transmission.subject_id.id for transmission in transmissions]
        )
        by_move = {
            transmission.subject_id.id: transmission for transmission in transmissions
        }

        entries = self._get_entries(moves, kind)
        for entry in entries:
            move = entry["__move__"]
            by_move[move.id]._add_attachment(
                Document(
                    move._l10n_gr_edi_generate_xml_content(
                        TEMPLATES[kind], {"invoice_values_list": [entry]}
                    ),
                    mimetype=XML_MIMETYPE,
                    name=self._get_filename(move),
                ),
            )

        content = moves._l10n_gr_edi_generate_xml_content(
            TEMPLATES[kind], {"invoice_values_list": entries}
        )
        responses = self._read_responses(
            transmissions.channel_id, ENDPOINTS[kind], content
        )

        return {
            by_move[entry["__move__"].id].id: verdict
            for index, entry in enumerate(entries)
            if (verdict := responses.get(index)) is not None
        }

    def _read_inbox(self, channel) -> list:
        window_start = (fields.Datetime.now() - timedelta(days=INBOX_DAYS)).strftime(
            "%d/%m/%Y"
        )
        response = channel._get_api_client().get(
            "RequestDocs",
            params={
                "mark": 0,
                "dateFrom": window_start,
                "dateTo": fields.Datetime.now().strftime("%d/%m/%Y"),
            },
            headers={"aade-user-id": channel.participant or ""},
        )
        root = etree.fromstring((response.get("body") or "").encode())
        return [
            Document(
                etree.tostring(element),
                mimetype=XML_MIMETYPE,
                name=f"mydata_received.{extension_for(XML_MIMETYPE)}",
            )
            for element in root.xpath('//*[local-name()="invoice"]')
        ]

    def _add_from_inbox(self, channel, documents) -> None:
        """Each received invoice becomes a draft bill and its classification.

        The mark is the authority's id for *their* document, which we quote when
        we classify the expense -- so what the receipt opens is a classification
        in draft, not a verdict on anything we sent.
        """
        company = channel.company_id or self.env.company
        moves = self.env["account.move"].sudo().with_company(company)

        pending = []
        for document in documents:
            mark = _find(document.tree, "mark")
            if not mark or moves.search_count(  # noqa: E8507 - one probe per document of the myDATA response
                [
                    ("l10n_gr_edi_mark", "=", mark),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            ):
                continue
            pending.append((mark, self._prepare_bill_vals(document.tree, company)))

        if not pending:
            return

        bills = moves.create([values for _mark, values in pending])
        self.env["exchange.transmission"].create(
            [
                {
                    "subject_id": f"account.move,{bill.id}",
                    "channel_id": channel.id,
                    "company_id": company.id,
                    "intent": "issue",
                    "state": "draft",
                    "document_kind": "mydata.classification",
                    "l10n_gr_edi_mark": mark,
                }
                for bill, (mark, _values) in zip(bills, pending, strict=True)
            ],
        )

    # HELPER METHODS

    def _prepare_bill_vals(self, tree, company) -> dict:
        lines = []
        for detail in tree.xpath('.//*[local-name()="invoiceDetails"]'):
            tax_amount = VAT_CATEGORY_AMOUNT[_find(detail, "vatCategory")]
            quantity = max(1.0, float(_find(detail, "quantity") or 1))
            lines.append(
                Command.create(
                    {
                        "price_unit": float(_find(detail, "netValue")) / quantity,
                        "quantity": quantity,
                        "tax_ids": self.env["account.tax"].search(  # noqa: E8507 - one lookup per line of the fetched document
                            [
                                ("amount", "=", tax_amount),
                                ("company_ids", "in", [company.id]),
                            ],
                            limit=1,
                        ),
                    },
                ),
            )

        issue_date = fields.Date.to_date(_find(tree, "issueDate"))
        invoice_type = _find(tree, "invoiceType")
        return {
            "state": "draft",
            "move_type": "in_invoice",
            "company_id": company.id,
            "partner_id": self.env["res.partner"]
            .search([("vat", "=", _find(tree, "vatNumber"))], limit=1)
            .id,
            "date": issue_date,
            "invoice_date": issue_date,
            "invoice_line_ids": lines,
            **(
                {"l10n_gr_edi_inv_type": invoice_type}
                if invoice_type in INVOICE_TYPES_HAVE_EXPENSE
                else {}
            ),
        }

    def _get_filename(self, move) -> str:
        stem = (move.name or str(move.id)).replace("/", "_")
        return f"mydata_{stem}.{extension_for(XML_MIMETYPE)}"

    def _get_kind(self, transmission) -> str:
        kind = (transmission.document_kind or "").rpartition(".")[2]
        if kind not in ENDPOINTS:
            raise LookupError(
                f"myDATA takes an invoice or an expense classification, "
                f"not {transmission.document_kind!r}",
            )
        return kind

    def _get_entries(self, moves, kind: str) -> list[dict]:
        builder = (
            moves._l10n_gr_edi_get_invoices_xml_vals
            if kind == "invoice"
            else moves._l10n_gr_edi_get_expense_classification_xml_vals
        )
        return builder()["invoice_values_list"]

    def _read_responses(self, channel, endpoint: str, content: bytes) -> dict:
        response = channel._get_api_client().post(
            endpoint,
            data=content,
            headers={"aade-user-id": channel.participant or ""},
        )
        root = etree.fromstring((response.get("body") or "").encode())

        verdicts = {}
        for element in root.xpath("//response"):
            index = int(element.findtext("index") or "1") - 1
            if element.findtext("statusCode") == "Success":
                verdicts[index] = Verdict(
                    state="accepted",
                    reference=element.findtext("classificationMark")
                    or element.findtext("invoiceMark")
                    or "",
                    values={
                        "l10n_gr_edi_mark": element.findtext("invoiceMark") or False,
                        "l10n_gr_edi_url": element.findtext("qrUrl") or False,
                    },
                )
            else:
                errors = element.xpath("./errors/error")
                verdicts[index] = Verdict(
                    state="rejected",
                    message="\n".join(
                        f"[{error.findtext('code')}] {error.findtext('message')}."
                        for error in errors
                    )
                    or self.env._("myDATA refused the document without saying why."),
                )
        return verdicts
