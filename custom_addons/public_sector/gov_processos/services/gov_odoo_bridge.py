from odoo import fields


class GovOdooBridge:
    """
    Converte o documento/processo para um payload canônico consumível pelo Typst.

    A V1 reaproveita o contexto documental já existente no módulo para reduzir
    risco de divergência entre o fluxo manual e o estruturado.
    """

    def __init__(self, doc, template=None):
        self.doc = doc
        self.template = template or doc.template_ref or doc.ai_template_id or doc._get_default_ai_template()
        self.processo = doc.processo_id
        self.company = self.processo.ug_id or doc.env.company

    def build(self):
        context = self.doc._build_ai_context(self.template, memory_block="")
        parameter_context = (
            self.processo.get_template_parameter_context(template=self.template)
            if self.processo
            else {}
        )
        payload = {
            "ente": self._build_ente(),
            "processo": self._build_processo(),
            "documento": self._build_documento(),
            "template": self._build_template(),
            "parametros": parameter_context,
            "contexto": context,
        }
        payload.update(context)
        return payload

    def _build_ente(self):
        company = self.company
        state = company.state_id
        return {
            "municipio": company.city or "",
            "estado": state.code or "",
            "nome_estado": state.name or "",
            "prefeitura": company.name or "",
            "secretaria": getattr(company, "secretaria_name", "") or company.name or "",
            "sigla_sec": getattr(company, "secretaria_sigla", "") or "",
            "endereco": " - ".join(filter(None, [company.street, company.street2])),
            "cep": company.zip or "",
            "telefone": company.phone or "",
            "cnpj": getattr(company, "cnpj_ug", "") or "",
            "exercicio": getattr(company, "exercicio_fiscal", "") or "",
        }

    def _build_processo(self):
        processo = self.processo
        return {
            "numero": processo.name or "",
            "assunto": processo.subject or "",
            "tipo": self.doc.process_type or "",
            "escopo": self.doc.process_scope or "",
            "origem": processo.origin_type or "",
            "responsavel": processo.responsible_id.name if processo.responsible_id else "",
            "data_doc": self._format_date(fields.Date.today()),
        }

    def _build_documento(self):
        doc = self.doc
        return {
            "nome": doc.name or "",
            "tipo": doc.doc_type or "",
            "versao": doc.version or 1,
            "modo_render": doc.render_mode or "manual_source",
            "checklist_mode": doc.checklist_mode or "",
            "area_requisitante": doc.dfd_area_requisitante or "",
            "objeto": doc.dfd_objeto or self.processo.subject or "",
            "justificativa": doc.dfd_justificativa or "",
            "quantidade": doc.dfd_quantidade or "",
            "valor_estimado": doc.dfd_valor_estimado or 0,
            "data_necessidade": self._format_date(doc.dfd_data_necessidade),
            "vinculo_ppa": doc.dfd_vinculo_ppa or "",
            "responsavel_tecnico": (
                doc.dfd_responsavel_tecnico.name if doc.dfd_responsavel_tecnico else ""
            ),
        }

    def _build_template(self):
        template = self.template
        return {
            "id": template.id if template else 0,
            "nome": template.name if template else "",
            "output_format": template.output_format if template else "",
            "versao_normativa": template.versao_normativa if template else "",
            "guidance_text": template.guidance_text if template else "",
        }

    @staticmethod
    def _format_date(value):
        if not value:
            return ""
        try:
            return fields.Date.to_string(value)
        except Exception:
            return str(value)
