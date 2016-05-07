# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.import copy
import logging

from itertools import groupby
from lxml import etree

from . import website
from odoo import api, fields, models, tools
from odoo.http import request

_logger = logging.getLogger(__name__)

class View(models.Model):
    _name = "ir.ui.view"
    _inherit = ["ir.ui.view", "website.seo.metadata"]

    page = fields.Boolean("Whether this view is a web page template (complete)")
    customize_show = fields.Boolean("Show As Optional Inherit")
    website_id = fields.Many2one('website', ondelete='cascade', string="Website")

    def unlink(self):
        res = super(View, self).unlink()
        self.clear_caches()
        return res

    def _sort_suitability_key(self):
        """
        Key function to sort views by descending suitability
        Suitability of a view is defined as follow:

        * if the view and request website_id are matched
        * then if the view has no set website
        """
        context_website_id = self.env.context.get('website_id', 1)
        website_id = self.website_id.id or 0
        different_website = context_website_id != website_id

        return (different_website, website_id)

    def filter_duplicate(self):
        """
        Filter current recordset only keeping the most suitable view per distinct key
        """
        filtered = self.browse([])
        for _, group in groupby(self, key=lambda r: r.key):
            filtered += sorted(group, key=lambda r: r._sort_suitability_key())[0]
        return filtered

    def _view_obj(self, view_id):
        if isinstance(view_id, basestring):
            if 'website_id' in self.env.context:
                domain = [('key', '=', view_id), '|', ('website_id', '=', False), ('website_id', '=', self.env.context['website_id'])]
                rec = self.search(domain, order='website_id')
            else:
                rec = self.search([('key', '=', view_id)])
            if rec:
                return rec.filter_duplicate()
            else:
                return self.evn.ref(view_id)
        elif isinstance(view_id, (int, long)):
            return self.browse(view_id)

        # assume it's already a view object (WTF?)
        return view_id

    # Returns all views (called and inherited) related to a view
    # Used by translation mechanism, SEO and optional templates
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
            extensions = view.inherit_children_ids.filtered('active')

        # Keep options in a deterministic order regardless of their applicability
        for extension in sorted(extensions, key=lambda v: v.id):
            for r in self._views_get(extension,
                    # only return optional grandchildren if this child is enabled
                    options=extension.active,
                    root=False):
                if r not in result:
                    result.append(r)
        return result

    @api.model
    @tools.ormcache_context('self.env.uid', 'xml_id', keys=('website_id',))
    def get_view_id(self, xml_id):
        if 'website_id' in self.env.context and not isinstance(xml_id, (int, long)):
            domain = [('key', '=', xml_id), '|', ('website_id', '=', self.env.context['website_id']), ('website_id', '=', False)]
            view_id = self.search(domain, order='website_id', limit=1).id or [None]
            if not view_id:
                _logger.warning("Could not find view object with xml_id '%s'" % (xml_id))
                raise ValueError('View %r in website %r not found' % (xml_id, self.env.context['website_id']))
        else:
            view_id = super(View, self).get_view_id(xml_id)
        return view_id

    @api.multi
    def render(self, values=None, engine='ir.qweb'):
        local_context = {}
        if request and getattr(request, 'website_enabled', False):
            engine = 'ir.qweb'
            qcontext = self._prepare_qcontext()

            # add some values
            if values:
                qcontext.update(values)

            # in edit mode ir.ui.view will tag nodes
            if not qcontext.get('translatable') and not qcontext.get('rendering_bundle'):
                if qcontext.get('editable'):
                    local_context['inherit_branding'] = True
                elif self.env.user.has_group('base.group_website_publisher'):
                    local_context['inherit_branding_auto'] = True

            if 'main_object' not in qcontext:
                qcontext['main_object'] = self

            values = qcontext
        return super(View, self.with_context(**local_context)).render(values=values, engine=engine)

    @api.model
    def _prepare_qcontext(self):
        local_context = dict(self.env.context)
        company = self.env['res.company'].sudo().browse(request.website.company_id.id)
        editable = request.website.is_publisher()
        translatable = editable and local_context.get('lang') != request.website.default_lang_code
        editable = not translatable and editable

        qcontext = dict(
            local_context,
            website=request.website,
            url_for=website.url_for,
            slug=website.slug,
            res_company=company,
            user_id=self.env['res.users'].browse(self._uid),
            default_lang_code=request.website.default_lang_code,
            languages=request.website.get_languages(),
            translatable=translatable,
            editable=editable,
            menu_data=self.env['ir.ui.menu'].load_menus_root() if request.website.is_user() else None,
        )
        return qcontext

    def customize_template_get(self, key, full=False, bundles=False):
        """ Get inherit view's informations of the template ``key``. By default, only
        returns ``customize_show`` templates (which can be active or not), if
        ``full=True`` returns inherit view's informations of the template ``key``.
        ``bundles=True`` returns also the asset bundles
        """
        IrModelData = self.env['ir.model.data']
        theme_view_id = IrModelData.xmlid_to_res_id('website.theme')
        user_groups = set(self.env.user.groups_id)
        views = self.with_context(active_test=False)._views_get(key, bundles=bundles)
        done = set()
        result = []
        for view in views:
            if not user_groups.issuperset(view.groups_id):
                continue
            if full or (view.customize_show and view.inherit_id.id != theme_view_id):
                if view.inherit_id not in done:
                    result.append({
                        'name': view.inherit_id.name,
                        'id': view.id,
                        'key': view.key,
                        'inherit_id': view.inherit_id.id,
                        'header': True,
                        'active': False
                    })
                    done.add(view.inherit_id)
                result.append({
                    'name': view.name,
                    'id': view.id,
                    'key': view.key,
                    'inherit_id': view.inherit_id.id,
                    'header': False,
                    'active': view.active,
                })
        return result
