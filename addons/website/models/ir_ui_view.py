# -*- coding: ascii -*-
import logging

from lxml import etree

from openerp import api, fields, models, tools
from openerp.addons.website.models import website
from openerp.http import request

_logger = logging.getLogger(__name__)


class View(models.Model):
    _name = "ir.ui.view"
    _inherit = ["ir.ui.view", "website.seo.metadata"]

    page = fields.Boolean("Whether this view is a web page template (complete)", default=False)
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
            if 'website_id' in (self.env.context or {}):
                domain = [('key', '=', view_id), '|', ('website_id', '=', False), ('website_id', '=', self.env.context.get('website_id'))]
                rec = self.search(domain, order='website_id')
            else:
                rec = self.search([('key', '=', view_id)], limit=1)
            if rec:
                return rec
            else:
                return self.env.ref(view_id, raise_if_not_found=True)
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

    #TODO MBA lets check
    @tools.ormcache_context('xml_id', keys=('website_id',))
    def get_view_id(self, xml_id):
        if self.env.context and 'website_id' in self.env.context and not isinstance(xml_id, (int, long)):
            domain = [('key', '=', xml_id), '|', ('website_id', '=', self.env.context['website_id']), ('website_id', '=', False)]
            view_id = self.search(domain, order='website_id', limit=1).id
            if not view_id:
                raise ValueError('View %r in website %r not found' % (xml_id, self.env.context['website_id']))
        else:
            view_id = super(View, self).get_view_id(xml_id)
        return view_id

    #TODO mba check later on
    @api.cr_uid_ids_context
    def render(self, cr, uid, id_or_xml_id, values=None, engine='ir.qweb', context=None):
        if request and getattr(request, 'website_enabled', False):
            engine = 'ir.qweb'

            if isinstance(id_or_xml_id, list):
                id_or_xml_id = id_or_xml_id[0]

            qcontext = self._prepare_qcontext(cr, uid, context=context)

            # add some values
            if values:
                qcontext.update(values)

            # in edit mode ir.ui.view will tag nodes
            if not qcontext.get('translatable') and not qcontext.get('rendering_bundle'):
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
    def _prepare_qcontext(self):
        company = self.env['res.company'].sudo().browse(request.website.company_id.id)

        editable = request.website.is_publisher()
        translatable = editable and self.env.context.get('lang') != request.website.default_lang_code
        editable = not translatable and editable

        qcontext = dict(
            self.env.context.copy(),
            website=request.website,
            url_for=website.url_for,
            slug=website.slug,
            res_company=company,
            user_id=self.env.user,
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
        theme_view_id = self.env.ref('website.theme').id
        user_groups = set(self.env.user.groups_id)
        views = self.with_context(active_test=False)._views_get(key, bundles=bundles)
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
