import json

from odoo import models


class AiAgent(models.Model):
    _inherit = 'ai.agent'

    # --------------------------------------------------
    # AI Tool methods for the website builder topic
    # --------------------------------------------------

    # Building blocks that require server-side setup and will crash if inserted via AI
    _EXCLUDED_SNIPPETS = {'s_website_form', 's_dynamic_snippet'}

    def _ai_tool_list_building_blocks(self):
        """List available Odoo website building blocks with their section and title."""
        snippets = self.env['ir.ui.view'].sudo().search([
            ('key', 'like', 'website.s_%'),
            ('type', '=', 'qweb'),
            ('key', 'not like', '%_option%'),
        ], order='key')

        blocks = []
        for snippet in snippets:
            key = snippet.key
            snippet_name = key.split('.')[-1] if '.' in key else key
            if snippet_name in self._EXCLUDED_SNIPPETS:
                continue
            blocks.append({
                'key': key,
                'name': snippet_name,
                'title': snippet.name or snippet_name,
            })
        return json.dumps(blocks)

    def _ai_tool_get_building_block_code(self, snippet_key):
        """Render and return the HTML of a specific building block template."""
        try:
            html = self.env['ir.qweb']._render(snippet_key, raise_if_not_found=False)
            if html:
                return str(html).strip()
            return f"Building block '{snippet_key}' not found."
        except Exception:
            return f"Error rendering building block '{snippet_key}'."

    def _ai_tool_apply_html_to_page(self, html='', action='append', section_index=None,
                                       content_replacements=None, class_operations=None):
        """Send changes to the frontend for application to the edited page.

        :param html: HTML content (for append/prepend/replace/replace_all)
        :param action: 'append', 'replace', 'remove', 'prepend', 'replace_all', 'edit_content'
        :param section_index: 1-based index of the target section
        :param content_replacements: list of {"selector": "...", "new_inner_html": "..."}
        :param class_operations: list of {"selector": "...", "add": "...", "remove": "..."}
               selector is optional — omit or use empty string to target the section element itself
        """
        payload = {'html': html, 'action': action}
        if section_index is not None:
            payload['sectionIndex'] = int(section_index)
        if content_replacements:
            if isinstance(content_replacements, str):
                content_replacements = json.loads(content_replacements)
            payload['contentReplacements'] = content_replacements
        if class_operations:
            if isinstance(class_operations, str):
                class_operations = json.loads(class_operations)
            payload['classOperations'] = class_operations
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'website_ai/apply_html',
            payload,
        )
        return f"HTML {action} applied to the page successfully."

    _USER_CUSTOM_RULES_URL = '/website/static/src/scss/user_custom_rules.scss'
    _USER_CUSTOM_RULES_BUNDLE = 'web.assets_frontend'

    def _ai_tool_list_custom_css_rules(self):
        """Read the current content of the user_custom_rules.scss file."""
        content = self.env['website.assets']._get_content_from_url(self._USER_CUSTOM_RULES_URL)
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        return content.strip() if content and content.strip() else "The user_custom_rules.scss file is empty (no custom CSS rules yet)."

    def _ai_tool_create_custom_css_rule(self, css_content):
        """Append SCSS rules to the user_custom_rules.scss file and reload assets."""
        # Read current content
        current = self.env['website.assets']._get_content_from_url(self._USER_CUSTOM_RULES_URL)
        if isinstance(current, bytes):
            current = current.decode('utf-8')

        # Append new rules to existing content
        new_content = current.rstrip() + '\n\n' + css_content.strip() + '\n'

        # Save via the standard website asset mechanism
        self.env['website.assets'].save_asset(
            self._USER_CUSTOM_RULES_URL,
            self._USER_CUSTOM_RULES_BUNDLE,
            new_content,
            'scss',
        )

        # Notify frontend to save the page and reload CSS bundles
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'website_ai/reload_css',
            {},
        )
        return f"Custom CSS rule added and assets reloaded."
