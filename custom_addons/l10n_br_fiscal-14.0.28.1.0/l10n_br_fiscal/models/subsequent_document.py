# Copyright 2018 KMEE INFORMATICA LTDA
#   Gabriel Cardoso de Faria <gabriel.cardoso@kmee.com.br>
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl)
#


from odoo import api, fields, models

from ..constants.fiscal import (
    MODELO_FISCAL_CFE,
    MODELO_FISCAL_CUPOM_FISCAL_ECF,
    MODELO_FISCAL_NFCE,
    SITUACAO_EDOC_CANCELADA,
)

SITUACAO_SUBSEQUENTE = (
    ("manual", "Manualmente"),
    ("nota_de_cupom", "Gerar Nota Fiscal de Cupons Fiscais"),
    ("nota_de_remessa", "Gerar Nota Fiscal de Remessa"),
)


class SubsequentDocument(models.Model):
    _name = "l10n_br_fiscal.subsequent.document"
    _description = "Subsequent Document"

    source_document_id = fields.Many2one(
        string="Source document",
        comodel_name="l10n_br_fiscal.document",
        required=True,
        ondelete="cascade",
    )

    subsequent_operation_id = fields.Many2one(
        string="Subsequent Operation",
        comodel_name="l10n_br_fiscal.subsequent.operation",
        required=True,
    )

    fiscal_operation_id = fields.Many2one(
        string="Related operation",
        comodel_name="l10n_br_fiscal.operation",
        required=True,
    )

    subsequent_document_id = fields.Many2one(
        string="Subsequent Document",
        comodel_name="l10n_br_fiscal.document",
        ondelete="set null",
        copy=False,
    )

    operation_performed = fields.Boolean(
        compute="_compute_operation_performed",
        default=False,
        copy=False,
    )

    # def _subsequent_payment_type(self):
    #     return (self.operation_id.ind_forma_pagamento or
    #             self.source_document_id.ind_forma_pagamento)
    #
    # def _subsequent_payment_condition(self):
    #     return (self.operation_id.condicao_pagamento_id or
    #             self.source_document_id.condicao_pagamento_id)

    def _subsequent_company(self):
        return self.fiscal_operation_id.company_id or self.source_document_id.company_id

    def _subsequent_partner(self):
        return (
            self.subsequent_operation_id.partner_id
            or self.source_document_id.partner_id
        )

    def _subsequent_referenced(self):
        if self.subsequent_operation_id.reference_document:
            return self.env.context.get(
                "referenciado_ids",
                self.source_document_id._prepare_referenced_subsequent(),
            )
        return []

    def generate_subsequent_document(self):
        self._generate_subsequent_document()

    def _generate_subsequent_document(self):
        if self.operation_performed:
            return self.subsequent_document_id

        new_doc = self.source_document_id.copy()

        new_doc.partner_id = self._subsequent_partner()
        new_doc.company_id = self._subsequent_company()
        new_doc.fiscal_operation_id = self.fiscal_operation_id
        new_doc.document_type_id = (
            self.subsequent_operation_id.operation_document_type_id
        )
        new_doc.document_serie_id = new_doc.document_type_id.get_document_serie(
            new_doc.company_id, new_doc.fiscal_operation_id
        )

        # new_doc.condicao_pagamento_id = \
        #     self._subsequent_payment_condition()
        # new_doc.tipo_pagamento = self._subsequent_payment_type()

        #
        # Reference document
        #
        reference_ids = self._subsequent_referenced()
        new_doc._document_reference(reference_ids)

        new_doc._onchange_fiscal_operation_id()
        new_doc.fiscal_line_ids.write(
            {"fiscal_operation_id": new_doc.fiscal_operation_id.id}
        )

        for item in new_doc.fiscal_line_ids:
            item._onchange_fiscal_operation_id()
            item._onchange_fiscal_operation_line_id()
            item._onchange_fiscal_taxes()

        document = new_doc
        document.action_document_confirm()
        self.subsequent_document_id = document

    @api.depends("subsequent_document_id.state_edoc")
    def _compute_operation_performed(self):
        for subseq in self:
            if not subseq.subsequent_document_id:
                subseq.operation_performed = False
            elif subseq.subsequent_document_id.state_edoc == SITUACAO_EDOC_CANCELADA:
                subseq.operation_performed = False
            else:
                subseq.operation_performed = True

    def show_subsequent_document(self):
        return {
            "name": "Subsequent Document",
            "type": "ir.actions.act_window",
            "target": "current",
            "views": [[False, "form"]],
            "res_model": "l10n_br_fiscal.document",
            "domain": [["id", "in", [self.subsequent_document_id.id]]],
            "res_id": self.subsequent_document_id.id,
        }

    def show_source_document(self):
        return {
            "name": "Source Document",
            "type": "ir.actions.act_window",
            "target": "current",
            "views": [[False, "form"]],
            "res_model": "l10n_br_fiscal.document",
            "domain": [["id", "in", [self.source_document_id.id]]],
            "res_id": self.source_document_id.id,
        }

    def unlink(self):
        for subsequent_id in self:
            if subsequent_id.operation_performed:
                raise UserWarning(
                    "The document cannot be deleted: the "
                    "subsequent document has already been "
                    "generated."
                )
        return super().unlink()

    def _confirms_document_generation(self):
        """We check if we can generate the subsequent document
        :return: True: allowing generation
        """
        result = False

        if self.subsequent_operation_id.generation_situation in [
            x for x, y in SITUACAO_SUBSEQUENTE
        ]:
            coupon = self.source_document_id.filtered(
                lambda document: document.document_type_id.code
                in (
                    MODELO_FISCAL_CFE,
                    MODELO_FISCAL_NFCE,
                    MODELO_FISCAL_CUPOM_FISCAL_ECF,
                )
            )
            if (
                coupon
                and self.subsequent_operation_id.generation_situation == "nota_de_cupom"
            ):
                result = True
            elif (
                self.subsequent_operation_id.generation_situation == "manual"
                and self.env.context.get("manual", False)
            ):
                result = True
            elif self.subsequent_operation_id.generation_situation == "nota_de_remessa":
                result = True
        elif (
            self.source_document_id.state_edoc
            == self.subsequent_operation_id.generation_situation
        ):
            result = True
        return result
