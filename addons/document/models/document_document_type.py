from datetime import date, timedelta
from typing import Any

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog

EXPIRING_SOON_DAYS = 30

_debug = DebugLog(__name__)


class DocumentDocument(models.Model):
    _inherit = "document.document"

    document_type_id = fields.Many2one(
        comodel_name="document.type",
        index=True,
        help="What kind of document this is. The type decides which attributes "
        "apply, starting with whether the document expires",
    )
    has_expiration = fields.Boolean(related="document_type_id.has_expiration")
    legal_number = fields.Char(
        help="Official registration, license, or identification number for this document"
    )
    issuer_id = fields.Many2one(
        comodel_name="res.partner",
        help="The organization or government authority that issued this document",
    )
    date_issued = fields.Date(help="The date when this document was officially issued")
    date_expiration = fields.Date(help="The date when this document expires")
    days_left = fields.Integer(
        compute="_compute_days_left",
        help="Number of days remaining until document expires (0 for non-expiring documents)",
    )
    expiration_state = fields.Selection(
        selection=[
            ("valid", "Valid"),
            ("expiring_soon", "Expiring Soon"),
            ("expired", "Expired"),
            ("missing", "Missing"),
        ],
        compute="_compute_expiration_state",
        store=True,
        help="Where the document stands against its expiration date: Valid (more "
        "than 30 days left), Expiring Soon (30 days or fewer), Expired (past date), "
        "Missing (the type expires and no date is set). Empty when the type does "
        "not expire",
    )

    is_renewable = fields.Boolean(related="document_type_id.is_renewable")
    renewal_document_id = fields.Many2one(
        comodel_name="document.document",
        help="The previous document this one renews",
    )
    renewal_ids = fields.One2many(
        comodel_name="document.document",
        inverse_name="renewal_document_id",
    )
    renewed_by_document_id = fields.Many2one(
        comodel_name="document.document",
        compute="_compute_renewed_by_document_id",
        help="The newer document that renewed this one",
    )
    renewal_count = fields.Integer(
        compute="_compute_renewal_count",
        recursive=True,
        help="Number of documents before this one in its renewal chain",
    )
    renewal_state = fields.Selection(
        selection=[
            ("due", "Renewal Due"),
            ("renewed", "Renewed"),
        ],
        compute="_compute_renewal_state",
        store=True,
        help="Where a renewable document stands: Renewal Due (expiring soon, "
        "expired or missing its date, and not yet renewed), Renewed (a newer "
        "document renews it). Empty when the type is not renewable or nothing is "
        "due",
    )

    _legal_number_uniq = models.UniqueIndex(
        "(legal_number, document_type_id, company_id) NULLS NOT DISTINCT "
        "WHERE legal_number IS NOT NULL",
        "Legal number must be unique per document type and company!",
    )
    _date_expiration_idx = models.Index(
        "(date_expiration) WHERE date_expiration IS NOT NULL"
    )
    _renewal_document_uniq = models.UniqueIndex(
        "(renewal_document_id) WHERE renewal_document_id IS NOT NULL",
        "A document can be renewed by only one document.",
    )

    @api.model
    def _get_expiration_today(self, company=None) -> date:
        company = company or self.env.company
        tz = company.partner_id.tz
        return fields.Date.context_today(self.with_context(tz=tz) if tz else self)

    def _group_by_expiration_today(self):
        for company, records in self.grouped("company_id").items():
            yield self._get_expiration_today(company or None), records

    def _iter_expiration_windows(self):
        companies = self.env["res.company"].search([])
        for company in [*companies, self.env["res.company"]]:
            yield (
                self._get_expiration_today(company or None),
                [("company_id", "=", company.id or False)],
            )

    @api.constrains("document_type_id", "company_id")
    def _check_document_type_company(self) -> None:
        for record in self:
            type_company = record.document_type_id.company_id
            if type_company and record.company_id and type_company != record.company_id:
                _debug.logic("document_type_refused", reason="company_mismatch")
                raise ValidationError(
                    self.env._(
                        "Document '%(doc)s' belongs to %(doc_company)s but its type "
                        "'%(type)s' belongs to %(type_company)s.",
                        doc=record.name,
                        doc_company=record.company_id.name,
                        type=record.document_type_id.name,
                        type_company=type_company.name,
                    )
                )

    @api.constrains("renewal_document_id")
    def _check_renewal_no_cycle(self) -> None:
        for record in self:
            seen = {record.id}
            current = record.renewal_document_id
            while current:
                if current.id in seen:
                    _debug.logic("renewal_refused", reason="cycle", document=record)
                    raise ValidationError(
                        self.env._(
                            "Circular reference detected in renewal chain. "
                            "Document '%(doc)s' would create a cycle.",
                            doc=record.name,
                        )
                    )
                seen.add(current.id)
                current = current.renewal_document_id

    @api.depends("renewal_ids")
    def _compute_renewed_by_document_id(self) -> None:
        for doc in self:
            doc.renewed_by_document_id = doc.renewal_ids[:1]

    @api.depends("renewal_document_id.renewal_count")
    def _compute_renewal_count(self) -> None:
        for doc in self:
            parent = doc.renewal_document_id
            doc.renewal_count = parent.renewal_count + 1 if parent else 0

    @api.depends("document_type_id.is_renewable", "expiration_state", "renewal_ids")
    def _compute_renewal_state(self) -> None:
        for doc in self:
            if not doc.document_type_id.is_renewable:
                doc.renewal_state = False
            elif doc.renewal_ids:
                doc.renewal_state = "renewed"
            elif doc.expiration_state in ("expiring_soon", "expired", "missing"):
                doc.renewal_state = "due"
            else:
                doc.renewal_state = False

    @api.depends("date_expiration", "company_id")
    def _compute_days_left(self) -> None:
        for today, records in self._group_by_expiration_today():
            for record in records:
                record.days_left = (
                    (record.date_expiration - today).days
                    if record.date_expiration
                    else 0
                )

    @api.depends("date_expiration", "company_id", "document_type_id.has_expiration")
    def _compute_expiration_state(self) -> None:
        for today, records in self._group_by_expiration_today():
            soon = today + timedelta(days=EXPIRING_SOON_DAYS)
            for record in records:
                if not record.document_type_id.has_expiration:
                    record.expiration_state = False
                elif not record.date_expiration:
                    record.expiration_state = "missing"
                elif record.date_expiration < today:
                    record.expiration_state = "expired"
                elif record.date_expiration <= soon:
                    record.expiration_state = "expiring_soon"
                else:
                    record.expiration_state = "valid"

    @api.onchange("document_type_id")
    def _onchange_document_type_id(self) -> None:
        doc_type = self.document_type_id
        if not doc_type:
            return
        if doc_type.folder_id:
            self.folder_id = doc_type.folder_id
        if doc_type.tag_ids:
            self.tag_ids = [Command.link(tag.id) for tag in doc_type.tag_ids]
        if not doc_type.has_expiration or not doc_type.default_validity_days:
            return
        if not self.date_issued:
            self.date_issued = fields.Date.context_today(self)
        if not self.date_expiration:
            self.date_expiration = self.date_issued + timedelta(
                days=doc_type.default_validity_days
            )

    def action_renew_document(self) -> dict[str, Any]:
        self.check_singleton()

        if not self.is_renewable:
            _debug.logic("renewal_refused", reason="type_not_renewable", document=self)
            raise UserError(self.env._("This document type is not renewable."))

        if self.renewed_by_document_id:
            _debug.logic("renewal_refused", reason="already_renewed", document=self)
            raise UserError(
                self.env._(
                    "Document '%(doc)s' has already been renewed by '%(renewal)s'. "
                    "Renew that one instead, so the chain stays a single line.",
                    doc=self.name,
                    renewal=self.renewed_by_document_id.name,
                )
            )

        today = fields.Date.context_today(self)
        validity = self.document_type_id.default_validity_days
        new_doc = self.copy(
            {
                "name": self.env._("%(name)s (Renewal)", name=self.name),
                "renewal_document_id": self.id,
                "attachment_id": False,
                "date_issued": today,
                "date_expiration": today + timedelta(days=validity)
                if validity
                else False,
                "legal_number": False,
            }
        )

        _debug.lifecycle(
            "renewed", source=self, renewal=new_doc, validity_days=validity
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "document.document",
            "res_id": new_doc.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _cron_refresh_expiration_state(self) -> bool:
        windows = Domain.OR(
            Domain(company_domain) & self._get_domain_stale_expiration(today)
            for today, company_domain in self._iter_expiration_windows()
        )
        stale = self.sudo().search(
            Domain("document_type_id.has_expiration", "=", True)
            & Domain("date_expiration", "!=", False)
            & windows
        )
        _debug.pipeline("expiration_refresh", stale=stale)
        if stale:
            stale._recompute_expiration_state()
        return True

    @api.model
    def _get_domain_stale_expiration(self, today) -> Domain:
        return Domain.OR(
            [
                Domain("date_expiration", "<", today)
                & Domain("expiration_state", "!=", "expired"),
                Domain("date_expiration", ">=", today)
                & Domain(
                    "date_expiration", "<=", today + timedelta(days=EXPIRING_SOON_DAYS)
                )
                & Domain("expiration_state", "=", "valid"),
            ]
        )

    def _recompute_expiration_state(self) -> None:
        _debug.pipeline("expiration_recomputed", documents=self)
        for field_name in ("expiration_state", "renewal_state"):
            self.env.add_to_compute(self._fields[field_name], self)
            self.flush_recordset([field_name])
