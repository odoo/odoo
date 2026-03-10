# Copyright (C) 2020  KMEE - www.kmee.com.br
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import json

from odoo import _, fields, models

from ..constants.fiscal import (
    SITUACAO_EDOC_A_ENVIAR,
    SITUACAO_EDOC_AUTORIZADA,
    SITUACAO_EDOC_CANCELADA,
    SITUACAO_EDOC_DENEGADA,
    SITUACAO_EDOC_EM_DIGITACAO,
    SITUACAO_EDOC_ENVIADA,
    SITUACAO_EDOC_INUTILIZADA,
    SITUACAO_EDOC_REJEITADA,
)

EDOC_2_CONFIRM = (
    SITUACAO_EDOC_EM_DIGITACAO,
    SITUACAO_EDOC_ENVIADA,
    SITUACAO_EDOC_A_ENVIAR,
    SITUACAO_EDOC_REJEITADA,
)

EDOC_CANCELED = (
    SITUACAO_EDOC_CANCELADA,
    SITUACAO_EDOC_DENEGADA,
    SITUACAO_EDOC_INUTILIZADA,
)


class Operation(models.Model):
    _inherit = "l10n_br_fiscal.operation"

    # TODO: Implementar no dashboard o valor total das operações, isso pode requer o
    #   uso de querys sql diretamente, não esquecer de aplicar as regras de acesso
    #   de forma manual ou usando o ORM:
    #         query = self._where_calc(args)
    #         self._apply_ir_rules(query, 'read')
    def _compute_kanban_dashboard(self):
        for operation in self:
            operation.kanban_dashboard = json.dumps(
                operation.get_operation_dashboard_data()
            )

    kanban_dashboard = fields.Text(compute="_compute_kanban_dashboard")

    color = fields.Integer(string="Color Index", default=0)

    def get_operation_dashboard_data(self):
        self.ensure_one()
        title = ""
        if self.fiscal_type in ("sale", "purchase"):
            title = (
                _("Bills to pay")
                if self.fiscal_type == "purchase"
                else _("Invoices owed to you")
            )

        number_2confirm = self._get_number_2confirm_documents()
        number_authorized = self._get_authorized_documents()
        number_cancelled = self._get_cancelled_documents()

        return {
            "number_2confirm": number_2confirm,
            "number_authorized": number_authorized,
            "number_cancelled": number_cancelled,
            "title": title,
        }

    def _fiscal_document_object(self):
        return self.env["l10n_br_fiscal.document"]

    def _get_number_2confirm_documents(self):
        return self._fiscal_document_object().search_count(
            [
                ("fiscal_operation_id.fiscal_type", "=", self.fiscal_type),
                ("fiscal_operation_id", "=", self.id),
                ("state_edoc", "in", EDOC_2_CONFIRM),
            ]
        )

    def _get_authorized_documents(self):
        return self._fiscal_document_object().search_count(
            [
                ("fiscal_operation_id.fiscal_type", "=", self.fiscal_type),
                ("fiscal_operation_id", "=", self.id),
                ("state_edoc", "=", SITUACAO_EDOC_AUTORIZADA),
            ]
        )

    def _get_cancelled_documents(self):
        return self._fiscal_document_object().search_count(
            [
                ("fiscal_operation_id.fiscal_type", "=", self.fiscal_type),
                ("fiscal_operation_id", "=", self.id),
                ("state_edoc", "in", EDOC_CANCELED),
            ]
        )

    def action_create_new(self):
        ctx = self._context.copy()
        model = "l10n_br_fiscal.document"
        if self.fiscal_operation_type == "out":
            ctx.update(
                {
                    "default_fiscal_operation_type": "out",
                    "default_fiscal_operation_id": self.id,
                }
            )
        elif self.fiscal_operation_type == "in":
            ctx.update(
                {
                    "default_fiscal_operation_type": "in",
                    "default_fiscal_operation_id": self.id,
                }
            )
        return {
            "name": _("Create invoice/bill"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": model,
            "view_id": self.env.ref("l10n_br_fiscal.document_form").id,
            "context": ctx,
        }

    def open_action(self):
        """return action based on type for related journals"""

        _fiscal_type_map = {
            "purchase": "in",
            "purchase_refund": "in",
            "return_in": "in",
            "sale": "out",
            "sale_refund": "out",
            "return_out": "out",
            "other": "out",
        }
        fiscal_operation_type = _fiscal_type_map[self.fiscal_type]

        action_name = self._context.get("action_name", False)

        if not action_name:
            action_name = (
                "document_out_action"
                if fiscal_operation_type == "out"
                else "document_in_action"
            )

        ctx = self._context.copy()
        ctx.pop("group_by", None)
        ctx.update(
            {
                "default_fiscal_operation_type": fiscal_operation_type,
            }
        )

        [action] = self.env.ref("l10n_br_fiscal.%s" % action_name).read()
        action["context"] = ctx
        action["domain"] = self._context.get("use_domain", [])
        action["domain"] += [
            ("fiscal_operation_id.fiscal_type", "=", self.fiscal_type),
            ("fiscal_operation_id", "=", self.id),
        ]
        if ctx.get("search_default_cancel"):
            action["domain"] += [("state_edoc", "in", EDOC_CANCELED)]
        elif ctx.get("search_default_authorized"):
            action["domain"] += [("state_edoc", "=", SITUACAO_EDOC_AUTORIZADA)]
        elif ctx.get("search_default_2confirm"):
            action["domain"] += [("state_edoc", "in", EDOC_2_CONFIRM)]
        return action
