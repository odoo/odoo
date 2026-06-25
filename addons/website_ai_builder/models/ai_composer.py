from lxml import html as lxml_html

from odoo import fields, models


class AiComposer(models.Model):
    _inherit = 'ai.composer'

    interface_key = fields.Selection(
        selection_add=[("website_builder_ai", "Edit a website page")],
        ondelete={"website_builder_ai": "cascade"},
    )

    def _get_initial_context(self, res_model=None, res_id=None, text_selection=None, text_of_editable=None):
        context_parts = super()._get_initial_context(res_model, res_id, text_selection, text_of_editable)
        if self.interface_key == "website_builder_ai" and text_of_editable:
            page_html = text_of_editable.strip()
            if page_html:
                structure = self._parse_page_structure(page_html)
                part = {'type': 'text', 'content': f"# Current page structure\n{structure}"}
                if context_parts:
                    context_parts.insert(-1, part)
                else:
                    context_parts = [
                        {'type': 'text', 'content': '<initial_session_context>Below is some initial info that might be useful'},
                        part,
                        {'type': 'text', 'content': '</initial_session_context>'},
                    ]
        return context_parts

    @staticmethod
    def _parse_page_structure(page_html):
        """Parse page HTML into a numbered section list for the AI."""
        try:
            doc = lxml_html.fromstring(f'<div>{page_html}</div>')
        except Exception:
            return "Could not parse page HTML."

        # Find sections inside #wrap, or all top-level sections
        wrap = doc.xpath('//*[@id="wrap"]')
        container = wrap[0] if wrap else doc
        sections = [c for c in container if hasattr(c, 'tag') and c.tag == 'section']

        if not sections:
            return "The page is empty — no sections found. Use action='append' to add new content."

        lines = ["The page currently has the following sections (use section_index to target them):"]
        for i, section in enumerate(sections, 1):
            snippet = section.get('data-snippet', 'custom')
            classes = section.get('class', '')
            text = section.text_content().strip()
            preview = ' '.join(text.split())[:120] if text else '(no text content)'
            lines.append(f"  {i}. [{snippet}] classes=\"{classes}\" — {preview}")
        return '\n'.join(lines)
