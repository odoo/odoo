# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup, escape_silent

from odoo import models


class IrQweb(models.AbstractModel):
    """ IrQweb object for rendering builder stuff
    """
    _inherit = 'ir.qweb'

    def _compile_root(self, element, compile_context):
        snippet_key = compile_context.pop('snippet-key', None)
        sub_call_key = compile_context.pop('snippet-sub-call-key', None)

        template = compile_context['ref_name']

        # We only add the 'data-snippet' & 'data-name' attrib once when
        # compiling the root node of the template.
        if not template or template not in {snippet_key, sub_call_key}:
            return super()._compile_root(element, compile_context)

        snippet_base_node = element
        if element.tag == 't':
            el_children = [child for child in list(element) if isinstance(child.tag, str) and child.tag != 't']
            if len(el_children) == 1:
                snippet_base_node = el_children[0]
            elif not el_children:
                # If there's not a valid base node we check if the base node is
                # a t-call to another template. If so the called template's base
                # node must take the current snippet key.
                el_children = [child for child in list(element) if isinstance(child.tag, str)]
                if len(el_children) == 1:
                    sub_call = el_children[0].get('t-call')
                    if sub_call:
                        el_children[0].set('t-options', f"{{'snippet-key': '{snippet_key}', 'snippet-sub-call-key': '{sub_call}'}}")
        # If it already has a data-snippet it is a saved or an
        # inherited snippet. Do not override it.
        if snippet_base_node.tag != 't' and 'data-snippet' not in snippet_base_node.attrib:
            snippet_base_node.attrib['data-snippet'] = \
                snippet_key.split('.', 1)[-1]
        # If it already has a data-name it is a saved or an
        # inherited snippet. Do not override it.
        snippet_name = compile_context.pop('snippet-name', None)
        if snippet_base_node.tag != 't' and snippet_name and 'data-name' not in snippet_base_node.attrib:
            snippet_base_node.attrib['data-name'] = snippet_name
        return super()._compile_root(element, compile_context)

    def _get_preload_attribute_xmlids(self):
        return super()._get_preload_attribute_xmlids() + ['t-snippet', 't-snippet-call']

    # compile directives

    def _compile_directive_snippet(self, el, compile_context, indent):
        key = el.attrib.pop('t-snippet')
        el.set('t-call', key)
        snippet_lang = self.env.context.get('snippet_lang')
        if snippet_lang:
            el.set('t-lang', f"'{snippet_lang}'")

        el.set('t-options', f"{{'snippet-key': {key!r}}}")
        view = self.env['ir.ui.view']._get_template_view(key)
        name = el.attrib.pop('string', view.name)
        thumbnail = el.attrib.pop('t-thumbnail', "oe-thumbnail")
        # If provided, this image is used as the placeholder in the snippet
        # dialog.
        image_preview = el.attrib.pop('t-image-preview', None)
        # If provided, this image is used as the snippet placeholder while
        # dragging the snippet onto the page (shown when over a dropzone).
        drag_image_preview = el.attrib.pop('t-drag-image-preview', None)
        # Forbid sanitize contains the specific reason:
        # - "true": always forbid
        # - "form": forbid if forms are sanitized
        forbid_sanitize = el.attrib.pop('t-forbid-sanitize', None)
        grid_column_span = el.attrib.pop('t-grid-column-span', None)
        snippet_group = el.attrib.pop('snippet-group', None)
        group = el.attrib.pop('group', None)
        label = el.attrib.pop('label', None)
        div = Markup('<div name="%s" data-oe-type="snippet" data-o-image-preview="%s" data-oe-thumbnail="%s" data-oe-snippet-id="%s" data-oe-snippet-key="%s" data-oe-keywords="%s" %s %s %s %s %s %s>') % (
            name,
            escape_silent(image_preview),
            thumbnail,
            view.id,
            key.split('.')[-1],
            escape_silent(el.findtext('keywords')),
            Markup('data-oe-forbid-sanitize="%s"') % forbid_sanitize if forbid_sanitize else '',
            Markup('data-o-grid-column-span="%s"') % grid_column_span if grid_column_span else '',
            Markup('data-o-snippet-group="%s"') % snippet_group if snippet_group else '',
            Markup('data-o-group="%s"') % group if group else '',
            Markup('data-o-label="%s"') % label if label else '',
            Markup('data-o-drag-image-preview="%s"') % drag_image_preview if drag_image_preview else '',
        )
        self._append_text(div, compile_context)
        code = self._compile_node(el, compile_context, indent)
        self._append_text('</div>', compile_context)
        return code

    def _compile_directive_snippet_call(self, el, compile_context, indent):
        key = el.attrib.pop('t-snippet-call')
        snippet_name = el.attrib.pop('string', None)
        el.set('t-call', key)
        el.set('t-options', f"{{'snippet-key': {key!r}, 'snippet-name': {snippet_name!r}}}")
        return self._compile_node(el, compile_context, indent)

    def _compile_directive_install(self, el, compile_context, indent):
        key = el.attrib.pop('t-install')
        thumbnail = el.attrib.pop('t-thumbnail', 'oe-thumbnail')
        image_preview = el.attrib.pop('t-image-preview', None)
        snippet_group = el.attrib.pop('snippet-group', None)
        group = el.attrib.pop('group', None)
        label = el.attrib.pop('label', None)
        name = el.attrib.pop('string', 'Snippet')
        if self.env.user.has_group('base.group_system'):
            module = self.env['ir.module.module'].search([('name', '=', key)])
            if not module or module.state == 'installed':
                return []
            div = Markup('<div name="%s" data-oe-type="snippet" data-module-id="%s" data-module-display-name="%s" data-o-image-preview="%s" data-oe-thumbnail="%s" %s %s %s><section/></div>') % (
                name,
                module.id,
                module.display_name,
                escape_silent(image_preview),
                thumbnail,
                Markup('data-o-snippet-group="%s"') % snippet_group if snippet_group else '',
                Markup('data-o-group="%s"') % group if group else '',
                Markup('data-o-label="%s"') % label if label else '',
            )
            self._append_text(div, compile_context)
        return []

    # order and ignore

    def _directives_eval_order(self):
        directives = super()._directives_eval_order()
        # Insert before "call" and "options" to use this "call" directive after this one
        index = directives.index('options') - 1
        directives.insert(index, 'snippet-call')

        # Insert before "att" as those may rely on static attributes like
        # "string" and "att" clears all of those
        index = directives.index('att') - 1
        directives.insert(index, 'snippet')
        directives.insert(index, 'install')
        return directives

    def _get_template_cache_keys(self):
        return super()._get_template_cache_keys() + ['snippet_lang']
