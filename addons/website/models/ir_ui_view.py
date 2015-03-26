# -*- coding: utf-8 -*-
import copy
import logging

from lxml import etree, html

from openerp import models, fields, api, tools
from openerp.addons.website.models import website
from openerp.http import request

_logger = logging.getLogger(__name__)


class View(models.Model):
    _inherit = "ir.ui.view"

    page = fields.Boolean("Whether this view is a web page template (complete)", default=False)
    website_meta_title = fields.Char("Website meta title", translate=True)
    website_meta_description = fields.Text("Website meta description", translate=True)
    website_meta_keywords = fields.Char("Website meta keywords", translate=True)
    customize_show = fields.Boolean("Show As Optional Inherit", default=False)
    website_id = fields.Many2one('website', ondelete='cascade', string="Website")

    @api.multi
    def unlink(self):
        res = super(View, self).unlink()
        self.clear_caches()
        return res

    @api.model
    def _view_obj(self, view_id):
        if isinstance(view_id, basestring):
            try:
                return self.env['ir.model.data'].xmlid_to_object(
                    view_id, raise_if_not_found=True
                )
            except:
                # Try to fallback on key instead of xml_id
                rec = self.search([('key', '=', view_id)])
                if rec:
                    _logger.info("Could not find view with `xml_id´ '%s', fallback on `key´" % (view_id))
                    return rec
                else:
                    raise
        elif isinstance(view_id, (int, long)):
            return self.browse(view_id)

        # assume it's already a view object (WTF?)
        return view_id

    # Returns all views (called and inherited) related to a view
    # Used by translation mechanism, SEO and optional templates
    @api.model
    def _views_get(self, view_id, options=True, bundles=False, root=True):
        """ For a given view ``view_id``, should return:

        * the view itself
        * all views inheriting from it, enabled or not
          - but not the optional children of a non-enabled child
        * all views called from it (via t-call)
        """

        try:
            view = self._view_obj(view_id)
        except ValueError:
            _logger.warning("Could not find view object with view_id '%s'" % (view_id))
            # Shall we log that ? Yes, you should !
            return []

        while root and view.inherit_id:
            view = view.inherit_id

        result = [view]

        node = etree.fromstring(view.arch)
        xpath = "//t[@t-call]"
        if bundles:
            xpath += "| //t[@t-call-assets]"
        for child in node.xpath(xpath):
            try:
                called_view = self._view_obj(child.get('t-call', child.get('t-call-assets')))
            except ValueError:
                continue
            if called_view not in result:
                result += self._views_get(called_view, options=options, bundles=bundles)

        extensions = view.inherit_children_ids
        if not options:
            # only active children
            extensions = (v for v in view.inherit_children_ids if v.active)

        # Keep options in a deterministic order regardless of their applicability
        for extension in sorted(extensions, key=lambda v: v.id):
            for r in self._views_get(
                    extension,
                    # only return optional grandchildren if this child is enabled
                    options=extension.active,
                    root=False):
                if r not in result:
                    result.append(r)
        return result

    @api.model
    def extract_embedded_fields(self, arch):
        return arch.xpath('//*[@data-oe-model != "ir.ui.view"]')

    @api.model
    def save_embedded_field(self, el):
        Model = self.env[el.get('data-oe-model')]
        field = el.get('data-oe-field')

        converter = self.env['website.qweb'].get_converter_for(el.get('data-oe-type'))
        value = converter.from_html(self.env.cr, self.env.uid, Model, Model._fields[field], el)

        if value is not None:
            # TODO: batch writes?
            Model.browse([int(el.get('data-oe-id'))]).write({
                field: value
            })

    @api.model
    def to_field_ref(self, el):
        # filter out meta-information inserted in the document
        attributes = dict((k, v) for k, v in el.items()
                          if not k.startswith('data-oe-'))
        attributes['t-field'] = el.get('data-oe-expression')

        out = html.html_parser.makeelement(el.tag, attrib=attributes)
        out.tail = el.tail
        return out

    @api.model
    def replace_arch_section(self, view_id, section_xpath, replacement):
        # the root of the arch section shouldn't actually be replaced as it's
        # not really editable itself, only the content truly is editable.

        [view] = self.browse([view_id])
        arch = etree.fromstring(view.arch.encode('utf-8'))
        # => get the replacement root
        if not section_xpath:
            root = arch
        else:
            # ensure there's only one match
            [root] = arch.xpath(section_xpath)

        root.text = replacement.text
        root.tail = replacement.tail
        # replace all children
        del root[:]
        for child in replacement:
            root.append(copy.deepcopy(child))

        return arch

    @tools.ormcache_context(accepted_keys=('website_id',))
    def get_view_id(self, cr, uid, xml_id, context=None):
        if context and 'website_id' in context and not isinstance(xml_id, (int, long)):
            domain = [('key', '=', xml_id), '|', ('website_id', '=', context['website_id']), ('website_id', '=', False)]
            [view_id] = self.search(cr, uid, domain, order='website_id', limit=1, context=context) or [None]
            if not view_id:
                raise ValueError('View %r in website %r not found' % (xml_id, context['website_id']))
        else:
            view_id = super(View, self).get_view_id(cr, uid, xml_id, context=context)
        return view_id

    @api.model
    def _prepare_qcontext(self):
        company = self.env['res.company'].sudo().browse(request.website.company_id.id)

        qcontext = dict(
            self.env.context.copy(),
            website=request.website,
            url_for=website.url_for,
            slug=website.slug,
            res_company=company,
            user_id=self.env.user,
            translatable=self.env.context.get('lang') != request.website.default_lang_code,
            editable=request.website.is_publisher(),
            menu_data=self.env['ir.ui.menu'].load_menus_root() if request.website.is_user() else None,
        )
        return qcontext

    @api.cr_uid_ids_context
    def render(self, cr, uid, id_or_xml_id, values=None, engine='ir.qweb', context=None):
        if request and getattr(request, 'website_enabled', False):
            engine = 'website.qweb'

            if isinstance(id_or_xml_id, list):
                id_or_xml_id = id_or_xml_id[0]

            qcontext = self._prepare_qcontext(cr, uid, context=context)

            # add some values
            if values:
                qcontext.update(values)

            # in edit mode ir.ui.view will tag nodes
            if qcontext.get('editable'):
                context = dict(context, inherit_branding=True)
            elif request.registry['res.users'].has_group(cr, uid, 'base.group_website_publisher'):
                context = dict(context, inherit_branding_auto=True)

            view_obj = request.website.get_template(id_or_xml_id)
            if 'main_object' not in qcontext:
                qcontext['main_object'] = view_obj

            values = qcontext

        return super(View, self).render(cr, uid, id_or_xml_id, values=values, engine=engine, context=context)

    @api.model
    def _pretty_arch(self, arch):
        # remove_blank_string does not seem to work on HTMLParser, and
        # pretty-printing with lxml more or less requires stripping
        # whitespace: http://lxml.de/FAQ.html#why-doesn-t-the-pretty-print-option-reformat-my-xml-output
        # so serialize to XML, parse as XML (remove whitespace) then serialize
        # as XML (pretty print)
        arch_no_whitespace = etree.fromstring(
            etree.tostring(arch, encoding='utf-8'),
            parser=etree.XMLParser(encoding='utf-8', remove_blank_text=True))
        return etree.tostring(
            arch_no_whitespace, encoding='unicode', pretty_print=True)

    @api.model
    def save(self, res_id, value, xpath=None):
        """ Update a view section. The view section may embed fields to write

        :param str model:
        :param int res_id:
        :param str xpath: valid xpath to the tag to replace
        """
        res_id = int(res_id)

        arch_section = html.fromstring(
            value, parser=html.HTMLParser(encoding='utf-8'))

        if xpath is None:
            # value is an embedded field on its own, not a view section
            self.save_embedded_field(arch_section)
            return

        for el in self.extract_embedded_fields(arch_section):
            self.save_embedded_field(el)

            # transform embedded field back to t-field
            el.getparent().replace(el, self.to_field_ref(el))

        arch = self.replace_arch_section(res_id, xpath, arch_section)
        self.browse(res_id).write({
            'arch': self._pretty_arch(arch)
        })

        view = self.sudo().browse(res_id)
        if view.model_data_id:
            view.model_data_id.write({'noupdate': True})

    def customize_template_get(self, key, full=False, bundles=False):
        """ Get inherit view's informations of the template ``key``. By default, only
        returns ``customize_show`` templates (which can be active or not), if
        ``full=True`` returns inherit view's informations of the template ``key``.
        ``bundles=True`` returns also the asset bundles
        """
        theme_view_id = self.env['ir.model.data'].xmlid_to_res_id('website.theme')
        user_groups = set(self.env.user.groups_id)
        views = self.with_context(active_test=False)._views_get(
            key, bundles=bundles)
        done = set()
        result = []
        for v in views:
            if not user_groups.issuperset(v.groups_id):
                continue
            if full or (v.customize_show and v.inherit_id.id != theme_view_id):
                if v.inherit_id not in done:
                    result.append({
                        'name': v.inherit_id.name,
                        'id': v.id,
                        'key': v.key,
                        'inherit_id': v.inherit_id.id,
                        'header': True,
                        'active': False
                    })
                    done.add(v.inherit_id)
                result.append({
                    'name': v.name,
                    'id': v.id,
                    'key': v.key,
                    'inherit_id': v.inherit_id.id,
                    'header': False,
                    'active': v.active,
                })
        return result

    def get_view_translations(self, xml_id, lang, field=['id', 'res_id', 'value', 'state', 'gengo_translation']):
        views = self.customize_template_get(xml_id, full=True)
        views_ids = [view.get('id') for view in views if view.get('active')]
        domain = [('type', '=', 'view'), ('res_id', 'in', views_ids), ('lang', '=', lang)]
        return self.env['ir.translation'].search_read(domain, field)

