# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from lxml import html, etree

from odoo import models
from odoo.tools import pycompat
from odoo.tools.translate import _

logger = logging.getLogger(__name__)


class WebsitePageGenerator(models.Model):
    _name = 'website.page'
    _inherit = 'website.page'

    def _construct_homepage(self, homepage_data):
        self._construct_page(homepage_data)
        self._create_footer(homepage_data)
        self._create_header(homepage_data)
        self._apply_website_themes(homepage_data)
        if homepage_data.get('footer'):
            self.env['web_editor.assets'].make_scss_customization(
                '/website/static/src/scss/options/user_values.scss',
                {
                    'footer-template': f"'imported-footer-{self.website_id.id}'",
                },
            )

    def _construct_page(self, page_data):
        html_block_list = page_data.get('body_html')
        if not html_block_list:
            return
        rendered_snippets = []
        nb_snippets = len(html_block_list)
        for i, snippet in enumerate(html_block_list, start=1):
            try:
                # Remove \ufeff character from the html (it is a BOM character that is not supported by lxml)
                el = html.fromstring(snippet.replace('\ufeff', ''))

                # TODO: Add the data-snippet attribute to identify the snippet
                # for compatibility code
                # el.attrib['data-snippet'] = snippet["name"]

                # Tweak the shape of the first snippet to connect it
                # properly with the header color in some themes
                if i == 1:
                    shape_el = el.xpath("//*[hasclass('o_we_shape')]")
                    if shape_el:
                        shape_el[0].attrib['class'] += ' o_header_extra_shape_mapping'

                # Tweak the shape of the last snippet to connect it
                # properly with the footer color in some themes
                if i == nb_snippets:
                    shape_el = el.xpath("//*[hasclass('o_we_shape')]")
                    if shape_el:
                        shape_el[0].attrib['class'] += ' o_footer_extra_shape_mapping'
                rendered_snippet = pycompat.to_text(etree.tostring(el))
                rendered_snippets.append(rendered_snippet)
            except ValueError as e:
                logger.warning("Error rendering snippet: %s", e)
        self.view_id.save(
            value="".join(rendered_snippets),
            xpath="(//div[hasclass('oe_structure')])[last()]",
        )

    def _create_header(self, homepage_data):
        # Remove all website menus, keep only the top menu "container"
        self.env['website.menu'].search([('website_id', '=', self.website_id.id)]).unlink()

        # Create the top menu of which to bind the menu buttons to.
        top_menu = self.env['website.menu'].create({
            'name': _('Top Menu for Website %s', self.website_id.id),
            'url': '/default-main-menu',
            'website_id': self.website_id.id,
        })
        for button in homepage_data.get('header', {}).get('buttons', []):
            if button.get('name', '').lower() in ['sign in', 'contact us']:
                continue  # those are Odoo menu already
            menu_content = button.get('menu_content')
            if menu_content:
                menu_type = menu_content.get('type')
                if menu_type == 'simple_menu':
                    # Create the parent menu
                    self._create_menu(button, top_menu)
                    # Get the parent menu id from the current website
                    parent_menu = self.env['website.menu'].search([('name', '=', button['name']), ('website_id', '=', self.website_id.id)])
                    # Create the submenu menu.
                    children_menus = button.get('menu_content', {}).get('content', [])
                    self.env['website.menu'].create([{
                        'name': child_menu['name'],
                        'url': child_menu['href'],
                        'parent_id': parent_menu.id,
                        'website_id': self.website_id.id} for child_menu in children_menus])
                elif menu_type == 'mega_menu':
                    # Create mega menu instead
                    button_name = button.get('name')
                    button_href = button.get('href')
                    mega_menu_content = button.get('menu_content', {}).get('content')
                    if not button_name or not button_href or not mega_menu_content:
                        return
                    self.env['website.menu'].create({
                        'name': button_name,
                        'url': button_href,
                        'website_id': self.website_id.id,
                        'parent_id': top_menu.id,
                        'is_mega_menu': True,
                        'mega_menu_content': mega_menu_content,
                    })
            else:
                self._create_menu(button, top_menu)

        # TODO: Need to try and set the level of transparency of the header overlay.
        header_position = homepage_data.get('header_position', 'regular')
        if header_position == 'regular':
            self.header_overlay = False
        elif header_position == 'over-the-content':
            self.header_overlay = True

    def _create_menu(self, menu, top_menu):
        menu_name = menu.get('name')
        menu_href = menu.get('href')
        if not menu_name or not menu_href:
            return
        self.env['website.menu'].create({
            'name': menu_name,
            'url': menu_href,
            'parent_id': top_menu.id,
            'website_id': self.website_id.id,
        })

    def _apply_website_themes(self, homepage_data):
        values = {}
        color_palette = homepage_data.get('color_palette', {})
        for i in range(1, 6):
            color = color_palette.get(f'o-color-{i}')
            if color:
                values[f'o-color-{i}'] = color

        header_color = homepage_data.get('header_color', {})
        if header_color:
            values.update({
                'menu': header_color.get('menu', "'NULL'"),
                'menu-gradient': header_color.get('menu-gradient', "'NULL'"),
                'menu-custom': header_color.get('menu-custom', "'NULL'"),
            })

        footer_color = homepage_data.get('footer_color', {})
        if footer_color:
            values.update({
                'footer': footer_color.get('footer', "'NULL'"),
                'footer-gradient': footer_color.get('footer-gradient', "'NULL'"),
                'footer-custom': footer_color.get('footer-custom', "'NULL'"),
                'copyright': footer_color.get('footer', "'NULL'"),
                'copyright-gradient': footer_color.get('footer-gradient', "'NULL'"),
                'copyright-custom': footer_color.get('footer-custom', "'NULL'"),
            })

        # TODO: Try add this new color palette as an option to the odoo editor list of options.
        self.env['web_editor.assets'].make_scss_customization(
            '/website/static/src/scss/options/colors/user_color_palette.scss',
            values,
        )

    def _create_footer(self, homepage_data):
        footer_html_list = homepage_data.get('footer', [])
        rendered_snippets = []
        for snippet in footer_html_list:
            try:
                # Process the footer html content (for example, an <img> element becomes <img/>.)
                el = html.fromstring(snippet)
                rendered_snippet = pycompat.to_text(etree.tostring(el))
                rendered_snippets.append(rendered_snippet)
            except ValueError as e:
                logger.warning(e)

        # Now generate the footer template.
        new_footer_template = f"""
    <xpath expr="//div[@id='footer']" position="replace">
        <div id="footer" class="oe_structure oe_structure_solo" t-ignore="true" t-if="not no_footer">{"".join(rendered_snippets)}</div>
    </xpath>"""

        self.env['ir.ui.view'].create({
            'name': 'Template WS Custom Footer',
            'type': 'qweb',
            'key': f'website_generator.template_ws_custom_footer_{self.website_id.id}',
            'arch': new_footer_template,
            'inherit_id': self.env['website'].with_context(website_id=self.website_id.id).viewref('website.layout').id,
            'website_id': self.website_id.id,
        })

        # And generate the footer snippet (such that it is selectable in the editor.)
        new_footer_snippet = f"""
    <xpath expr="//we-select[@data-variable='footer-template']" position="inside">
        <we-button title="Imported Footer"
            class="position-relative"
            data-customize-website-views="website_generator.template_ws_custom_footer_{self.website_id.id}"
            data-customize-website-variable="'imported-footer-{self.website_id.id}'"
            data-img="/website_generator/static/src/img/footer_template_imported.svg">
            <span class="badge rounded-pill bg-info position-absolute ms-4" style="top: 10px; left: 4px;">
                <i class="fa fa-gears"></i>
                Imported
            </span>
        </we-button>
    </xpath>"""

        self.env['ir.ui.view'].create({
            'name': 'WS Custom Footer',
            'type': 'qweb',
            'key': f'website.ws_custom_footer{self.website_id.id}',
            'arch': new_footer_snippet,
            'inherit_id': self.env.ref('website.snippet_options').id,
            'website_id': self.website_id.id,
        })
