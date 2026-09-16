from __future__ import annotations

from typing import TYPE_CHECKING

from odoo import api, models

if TYPE_CHECKING:
    from odoo.libs.documents import Document

    from ..tools import Verdict


class ExchangeProtocol(models.AbstractModel):
    _name = "exchange.protocol"
    _description = "Exchange Protocol"

    _protocol_code = None
    _protocol_label = None
    _document_kinds: dict[str, str] = {}
    _batch_size = 1

    # HELPER METHODS

    @api.model
    def _get_protocols(self) -> dict[str, str]:
        protocols: dict[str, str] = {}
        root = self.env.registry.get("exchange.protocol")
        if not root:
            return protocols

        pending = list(root._inherit_children)
        seen = set()
        while pending:
            name = pending.pop(0)
            if name in seen or name == "exchange.protocol":
                continue
            seen.add(name)

            model_cls = self.env.registry.get(name)
            if not model_cls:
                continue
            pending.extend(model_cls._inherit_children)

            code = getattr(model_cls, "_protocol_code", None)
            if code:
                protocols[code] = name
        return protocols

    @api.model
    def _selection_protocol(self) -> list[tuple[str, str]]:
        options = []
        for code, model_name in self._get_protocols().items():
            model_cls = self.env.registry[model_name]
            label = getattr(model_cls, "_protocol_label", None) or getattr(
                model_cls, "_description", code
            )
            options.append((code, label))
        return sorted(options, key=lambda option: option[1])

    @api.model
    def _selection_document_kind(self) -> list[tuple[str, str]]:
        options = []
        for code, model_name in self._get_protocols().items():
            model_cls = self.env.registry[model_name]
            protocol_label = getattr(model_cls, "_protocol_label", None) or code
            for kind, label in (
                getattr(model_cls, "_document_kinds", None) or {}
            ).items():
                options.append((f"{code}.{kind}", f"{protocol_label}: {label}"))
        return sorted(options, key=lambda option: option[1])

    @api.model
    def _get_document_kind(self, protocol_code: str, kind: str) -> str:
        known = (
            getattr(
                self.env.registry[self._get_protocols()[protocol_code]],
                "_document_kinds",
                None,
            )
            or {}
        )
        if kind not in known:
            raise LookupError(
                f"Protocol {protocol_code!r} declares no document kind {kind!r}. "
                f"Known kinds: {sorted(known)}",
            )
        return f"{protocol_code}.{kind}"

    @api.model
    def _get_protocol(self, code: str):
        model_name = self._get_protocols().get(code)
        if not model_name:
            raise LookupError(
                f"No exchange protocol declares the code {code!r}. "
                f"Known codes: {sorted(self._get_protocols())}",
            )
        return self.env[model_name]

    # PROTOCOL METHODS

    def _prepare_message(self, transmission) -> Document:
        raise NotImplementedError(
            f"{self._name} must build the document it sends",
        )

    def _get_message_errors(self, transmission) -> list[str]:
        return []

    def _seal_message(self, transmission, document: Document) -> Document:
        return document

    def _send_message(self, transmission, document: Document) -> Verdict:
        raise NotImplementedError(
            f"{self._name} must hand its document to the counterparty",
        )

    def _send_batch(self, transmissions) -> dict[int, Verdict]:
        verdicts = {}
        for transmission in transmissions:
            document = self._seal_message(
                transmission, self._prepare_message(transmission)
            )
            transmission._add_attachment(document)
            verdicts[transmission.id] = self._send_message(transmission, document)
        return verdicts

    def _read_verdict(self, transmission) -> Verdict | None:
        return None

    def _read_inbox(self, channel) -> list[Document]:
        return []

    def _add_from_inbox(self, channel, documents) -> None:
        raise NotImplementedError(
            f"{self._name} reads an inbox but does not say what to do with what "
            "it finds. _add_from_inbox lives here rather than on "
            "exchange.transmission because two protocols in one database would "
            "otherwise share one override.",
        )
