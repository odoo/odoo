import hashlib

from odoo import _
from odoo.exceptions import UserError


class GovTemplateRegistry:
    """
    Resolve o conteúdo Typst a partir de gov.ai.template.

    O backend atual do módulo guarda template Typst como texto em banco.
    """

    _TYPST_FIELDS = ("typst_template", "source_native_text")

    def __init__(self, env):
        self.env = env

    def resolve_text(self, template_record):
        if not template_record:
            raise UserError(_("Nenhum template Typst selecionado."))

        for field_name in self._TYPST_FIELDS:
            value = getattr(template_record, field_name, None)
            if value and value.strip():
                return value

        raise UserError(
            _("Template '%s' nao possui conteudo Typst configurado.")
            % template_record.name
        )

    def resolve_sha256(self, template_record):
        text = self.resolve_text(template_record)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
