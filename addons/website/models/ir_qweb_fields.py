# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from markupsafe import Markup

from odoo import api, models, _
from odoo.addons.website.tools import add_form_signature, parse_visibility_timestamp


class IrQwebFieldContact(models.AbstractModel):
    _inherit = 'ir.qweb.field.contact'

    @api.model
    def get_available_options(self):
        options = super().get_available_options()
        options.update(
            website_description=dict(type='boolean', string=_('Display the website description')),
            UserBio=dict(type='boolean', string=_('Display the biography')),
            badges=dict(type='boolean', string=_('Display the badges'))
        )
        return options


class IrQwebFieldHtml(models.AbstractModel):
    _inherit = 'ir.qweb.field.html'

    def _post_processing_att(self, tag, attrib):
        self.env['ir.qweb']._copy_translate_attributes(attrib)
        return super()._post_processing_att(tag, attrib)

    def _remove_out_of_datetime_range_elements(self, html_fragment, is_in_range):
        """ Remove the conditionally-visible elements of ``html_fragment`` that are
        out of their visibility datetime range. ``is_in_range`` gets the two
        limits and returns True if the element is visible. """
        xpath = './/*[@data-visibility="conditional"][@data-visibility-from or @data-visibility-until]'
        for el in html_fragment.xpath(xpath):
            visible_from = parse_visibility_timestamp(el.get('data-visibility-from'))
            visible_until = parse_visibility_timestamp(el.get('data-visibility-until'))
            if is_in_range(visible_from, visible_until):
                continue
            parent = el.getparent()
            if el.tail:
                previous = el.getprevious()
                if previous is not None:
                    previous.tail = (previous.tail or '') + el.tail
                else:
                    parent.text = (parent.text or '') + el.tail
            parent.remove(el)

    @api.model
    def value_to_html(self, value, options):
        """ This method handles two cases.
            1. The field contains a form which may need a security signature.
            2. The field contains an element supposed to be visible only in a
               specific datetime range. """
        res = super().value_to_html(value, options)
        if not res:
            return res

        has_form = '<form' in res  # Efficient check
        # Ignore the datetime range if branding is active. In this case, keep
        # the element in the HTML even if it is out of range, so that the user
        # can edit or translate it.
        has_datetime_range = (
            not options.get('inherit_branding')
            and not self.env.context.get('edit_translations')
            and ('data-visibility-from' in res or 'data-visibility-until' in res)
        )
        if has_form or has_datetime_range:
            # The usage of `fromstring`, `HTMLParser`, `tostring` and `Markup`
            # is replicating what is done in the `super()` implementation.
            body = etree.fromstring("<body>%s</body>" % res, etree.HTMLParser())[0]
            if has_form:
                add_form_signature(body, self.sudo().env)
            if has_datetime_range:
                self._remove_out_of_datetime_range_elements(body, self.env['ir.qweb']._check_datetime_visibility)
            res = Markup(etree.tostring(body, encoding='unicode', method='html')[6:-7])

        return res
