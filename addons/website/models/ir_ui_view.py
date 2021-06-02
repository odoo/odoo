# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import uuid
from itertools import groupby

from odoo import api, fields, models, _
from odoo import tools
from odoo.addons.http_routing.models.ir_http import url_for
from odoo.osv import expression
from odoo.http import request

_logger = logging.getLogger(__name__)


class View(models.Model):

    _name = "ir.ui.view"
    _inherit = ["ir.ui.view", "website.seo.metadata"]

    customize_show = fields.Boolean("Show As Optional Inherit", default=False)
    website_id = fields.Many2one('website', ondelete='cascade', string="Website")
    page_ids = fields.One2many('website.page', 'view_id')
    first_page_id = fields.Many2one('website.page', string='Website Page', help='First page linked to this view', compute='_compute_first_page_id')
    track = fields.Boolean(string='Track', default=False, help="Allow to specify for one page of the website to be trackable or not")

    def _compute_first_page_id(self):
        for view in self:
            view.first_page_id = self.env['website.page'].search([('view_id', '=', view.id)], limit=1)

    def name_get(self):
        if not self._context.get('display_website') and not self.env.user.has_group('website.group_multi_website'):
            return super(View, self).name_get()

        res = []
        for view in self:
            view_name = view.name
            if view.website_id:
                view_name += ' [%s]' % view.website_id.name
            res.append((view.id, view_name))
        return res

    def write(self, vals):
        '''COW for ir.ui.view. This way editing websites does not impact other
        websites. Also this way newly created websites will only
        contain the default views.
        '''
        current_website_id = self.env.context.get('website_id')
        if not current_website_id or self.env.context.get('no_cow'):
            return super(View, self).write(vals)

        # We need to consider inactive views when handling multi-website cow
        # feature (to copy inactive children views, to search for specific
        # views, ...)
        for view in self.with_context(active_test=False):
            # Make sure views which are written in a website context receive
            # a value for their 'key' field
            if not view.key and not vals.get('key'):
                view.with_context(no_cow=True).key = 'website.key_%s' % str(uuid.uuid4())[:6]

            # No need of COW if the view is already specific
            if view.website_id:
                super(View, view).write(vals)
                continue

            # Ensure the cache of the pages stay consistent when doing COW.
            # This is necessary when writing view fields from a page record
            # because the generic page will put the given values on its cache
            # but in reality the values were only meant to go on the specific
            # page. Invalidate all fields and not only those in vals because
            # other fields could have been changed implicitly too.
            pages = view.page_ids
            pages.flush(records=pages)
            pages.invalidate_cache(ids=pages.ids)

            # If already a specific view for this generic view, write on it
            website_specific_view = view.search([
                ('key', '=', view.key),
                ('website_id', '=', current_website_id)
            ], limit=1)
            if website_specific_view:
                super(View, website_specific_view).write(vals)
                continue

            # Set key to avoid copy() to generate an unique key as we want the
            # specific view to have the same key
            copy_vals = {'website_id': current_website_id, 'key': view.key}
            # Copy with the 'inherit_id' field value that will be written to
            # ensure the copied view's validation works
            if vals.get('inherit_id'):
                copy_vals['inherit_id'] = vals['inherit_id']
            website_specific_view = view.copy(copy_vals)

            view._create_website_specific_pages_for_view(website_specific_view,
                                                         view.env['website'].browse(current_website_id))

            for inherit_child in view.inherit_children_ids.filter_duplicate().sorted(key=lambda v: (v.priority, v.id)):
                if inherit_child.website_id.id == current_website_id:
                    # In the case the child was already specific to the current
                    # website, we cannot just reattach it to the new specific
                    # parent: we have to copy it there and remove it from the
                    # original tree. Indeed, the order of children 'id' fields
                    # must remain the same so that the inheritance is applied
                    # in the same order in the copied tree.
                    child = inherit_child.copy({'inherit_id': website_specific_view.id, 'key': inherit_child.key})
                    inherit_child.inherit_children_ids.write({'inherit_id': child.id})
                    inherit_child.unlink()
                else:
                    # Trigger COW on inheriting views
                    inherit_child.write({'inherit_id': website_specific_view.id})

            super(View, website_specific_view).write(vals)

        return True

    def _load_records_write_on_cow(self, cow_view, inherit_id, values):
        inherit_id = self.search([
            ('key', '=', self.browse(inherit_id).key),
            ('website_id', 'in', (False, cow_view.website_id.id)),
        ], order='website_id', limit=1).id
        values['inherit_id'] = inherit_id
        cow_view.with_context(no_cow=True).write(values)

    def _create_all_specific_views(self, processed_modules):
        """ When creating a generic child view, we should
            also create that view under specific view trees (COW'd).
            Top level view (no inherit_id) do not need that behavior as they
            will be shared between websites since there is no specific yet.
        """
        # Only for the modules being processed
        regex = '^(%s)[.]' % '|'.join(processed_modules)
        # Retrieve the views through a SQl query to avoid ORM queries inside of for loop
        # Retrieves all the views that are missing their specific counterpart with all the
        # specific view parent id and their website id in one query
        query = """
            SELECT generic.id, ARRAY[array_agg(spec_parent.id), array_agg(spec_parent.website_id)]
              FROM ir_ui_view generic
        INNER JOIN ir_ui_view generic_parent ON generic_parent.id = generic.inherit_id
        INNER JOIN ir_ui_view spec_parent ON spec_parent.key = generic_parent.key
         LEFT JOIN ir_ui_view specific ON specific.key = generic.key AND specific.website_id = spec_parent.website_id
             WHERE generic.type='qweb'
               AND generic.website_id IS NULL
               AND generic.key ~ %s
               AND spec_parent.website_id IS NOT NULL
               AND specific.id IS NULL
          GROUP BY generic.id
        """
        self.env.cr.execute(query, (regex, ))
        result = dict(self.env.cr.fetchall())

        for record in self.browse(result.keys()):
            specific_parent_view_ids, website_ids = result[record.id]
            for specific_parent_view_id, website_id in zip(specific_parent_view_ids, website_ids):
                record.with_context(website_id=website_id).write({
                    'inherit_id': specific_parent_view_id,
                })
        super(View, self)._create_all_specific_views(processed_modules)

    def unlink(self):
        '''This implements COU (copy-on-unlink). When deleting a generic page
        website-specific pages will be created so only the current
        website is affected.
        '''
        current_website_id = self._context.get('website_id')

        if current_website_id and not self._context.get('no_cow'):
            for view in self.filtered(lambda view: not view.website_id):
                for website in self.env['website'].search([('id', '!=', current_website_id)]):
                    # reuse the COW mechanism to create
                    # website-specific copies, it will take
                    # care of creating pages and menus.
                    view.with_context(website_id=website.id).write({'name': view.name})

        specific_views = self.env['ir.ui.view']
        if self and self.pool._init:
            for view in self.filtered(lambda view: not view.website_id):
                specific_views += view._get_specific_views()

        result = super(View, self + specific_views).unlink()
        self.clear_caches()
        return result

    def _create_website_specific_pages_for_view(self, new_view, website):
        for page in self.page_ids:
            # create new pages for this view
            page.copy({
                'view_id': new_view.id,
                'is_published': page.is_published,
            })

    @api.model
    def get_related_views(self, key, bundles=False):
        '''Make this only return most specific views for website.'''
        # get_related_views can be called through website=False routes
        # (e.g. /web_editor/get_assets_editor_resources), so website
        # dispatch_parameters may not be added. Manually set
        # website_id. (It will then always fallback on a website, this
        # method should never be called in a generic context, even for
        # tests)
        self = self.with_context(website_id=self.env['website'].get_current_website().id)
        return super(View, self).get_related_views(key, bundles=bundles)

    def filter_duplicate(self):
        """ Filter current recordset only keeping the most suitable view per distinct key.
            Every non-accessible view will be removed from the set:
              * In non website context, every view with a website will be removed
              * In a website context, every view from another website
        """
        current_website_id = self._context.get('website_id')
        most_specific_views = self.env['ir.ui.view']
        if not current_website_id:
            return self.filtered(lambda view: not view.website_id)

        for view in self:
            # specific view: add it if it's for the current website and ignore
            # it if it's for another website
            if view.website_id and view.website_id.id == current_website_id:
                most_specific_views |= view
            # generic view: add it only if, for the current website, there is no
            # specific view for this view (based on the same `key` attribute)
            elif not view.website_id and not any(view.key == view2.key and view2.website_id and view2.website_id.id == current_website_id for view2 in self):
                most_specific_views |= view

        return most_specific_views

    @api.model
    def _view_get_inherited_children(self, view):
        extensions = super(View, self)._view_get_inherited_children(view)
        return extensions.filter_duplicate()

    @api.model
    def _view_obj(self, view_id):
        ''' Given an xml_id or a view_id, return the corresponding view record.
            In case of website context, return the most specific one.
            :param view_id: either a string xml_id or an integer view_id
            :return: The view record or empty recordset
        '''
        if isinstance(view_id, str) or isinstance(view_id, int):
            return self.env['website'].viewref(view_id)
        else:
            # It can already be a view object when called by '_views_get()' that is calling '_view_obj'
            # for it's inherit_children_ids, passing them directly as object record. (Note that it might
            # be a view_id from another website but it will be filtered in 'get_related_views()')
            return view_id if view_id._name == 'ir.ui.view' else self.env['ir.ui.view']

    @api.model
    def _get_inheriting_views_arch_website(self, view_id):
        return self.env['website'].browse(self._context.get('website_id'))

    @api.model
    def _get_inheriting_views_arch_domain(self, view_id, model):
        domain = super(View, self)._get_inheriting_views_arch_domain(view_id, model)
        current_website = self._get_inheriting_views_arch_website(view_id)
        website_views_domain = current_website.website_domain()
        # when rendering for the website we have to include inactive views
        # we will prefer inactive website-specific views over active generic ones
        if current_website:
            domain = [leaf for leaf in domain if 'active' not in leaf]

        return expression.AND([website_views_domain, domain])

    @api.model
    def get_inheriting_views_arch(self, view_id, model):
        if not self._context.get('website_id'):
            return super(View, self).get_inheriting_views_arch(view_id, model)

        get_inheriting_self = self.with_context(active_test=False)
        if self.pool._init and not self._context.get('load_all_views'):
            view = self.browse(view_id)
            if view.website_id:
                original_view = view._get_original_view()
                original_keys = self.with_context(website_id=False)._get_inheriting_views(original_view.id, model).mapped('key')
                specific_views = self.search([('key', 'in', original_keys), ('website_id', '=', self._context.get('website_id'))])
                check_view_ids = list(self._context.get('check_view_ids') or ()) + specific_views.ids
                get_inheriting_self = self.with_context(check_view_ids=check_view_ids)
        inheriting_views = super(View, get_inheriting_self).get_inheriting_views_arch(view_id, model)

        # prefer inactive website-specific views over active generic ones
        inheriting_views = self.browse([view[1] for view in inheriting_views]).filter_duplicate().filtered('active')

        return [(view.arch, view.id) for view in inheriting_views]

    @api.model
    @tools.ormcache_context('self.env.uid', 'self.env.su', 'xml_id', keys=('website_id',))
    def get_view_id(self, xml_id):
        """If a website_id is in the context and the given xml_id is not an int
        then try to get the id of the specific view for that website, but
        fallback to the id of the generic view if there is no specific.

        If no website_id is in the context, it might randomly return the generic
        or the specific view, so it's probably not recommanded to use this
        method. `viewref` is probably more suitable.

        Archived views are ignored (unless the active_test context is set, but
        then the ormcache_context will not work as expected).
        """
        if 'website_id' in self._context and not isinstance(xml_id, int):
            current_website = self.env['website'].browse(self._context.get('website_id'))
            domain = ['&', ('key', '=', xml_id)] + current_website.website_domain()

            view = self.search(domain, order='website_id', limit=1)
            if not view:
                _logger.warning("Could not find view object with xml_id '%s'", xml_id)
                raise ValueError('View %r in website %r not found' % (xml_id, self._context['website_id']))
            return view.id
        return super(View, self).get_view_id(xml_id)

    def _get_original_view(self):
        """Given a view, retrieve the original view it was COW'd from.
        The given view might already be the original one. In that case it will
        (and should) return itself.
        """
        self.ensure_one()
        domain = [('key', '=', self.key), ('model_data_id', '!=', None)]
        return self.with_context(active_test=False).search(domain, limit=1)  # Useless limit has multiple xmlid should not be possible

    def render(self, values=None, engine='ir.qweb', minimal_qcontext=False):
        """ Render the template. If website is enabled on request, then extend rendering context with website values. """
        new_context = dict(self._context)
        if request and getattr(request, 'is_frontend', False):

            editable = request.website.is_publisher()
            translatable = editable and self._context.get('lang') != request.website.default_lang_id.code
            editable = not translatable and editable

            # in edit mode ir.ui.view will tag nodes
            if not translatable and not self.env.context.get('rendering_bundle'):
                if editable:
                    new_context = dict(self._context, inherit_branding=True)
                elif request.env.user.has_group('website.group_website_publisher'):
                    new_context = dict(self._context, inherit_branding_auto=True)
            if values and 'main_object' in values:
                if request.env.user.has_group('website.group_website_publisher'):
                    func = getattr(values['main_object'], 'get_backend_menu_id', False)
                    values['backend_menu_id'] = func and func() or self.env.ref('website.menu_website_configuration').id

                # Fallback incase main_object dont't inherit 'website.seo.metadata'
                if not hasattr(values['main_object'], 'get_website_meta'):
                    values['main_object'].get_website_meta = lambda: {}

        if self._context != new_context:
            self = self.with_context(new_context)
        return super(View, self).render(values, engine=engine, minimal_qcontext=minimal_qcontext)

    @api.model
    def _prepare_qcontext(self):
        """ Returns the qcontext : rendering context with website specific value (required
            to render website layout template)
        """
        qcontext = super(View, self)._prepare_qcontext()

        if request and getattr(request, 'is_frontend', False):
            Website = self.env['website']
            editable = request.website.is_publisher()
            translatable = editable and self._context.get('lang') != request.env['ir.http']._get_default_lang().code
            editable = not translatable and editable

            cur = Website.get_current_website()
            if self.env.user.has_group('website.group_website_publisher') and self.env.user.has_group('website.group_multi_website'):
                qcontext['multi_website_websites_current'] = {'website_id': cur.id, 'name': cur.name, 'domain': cur._get_http_domain()}
                qcontext['multi_website_websites'] = [
                    {'website_id': website.id, 'name': website.name, 'domain': website._get_http_domain()}
                    for website in Website.search([]) if website != cur
                ]

                cur_company = self.env.company
                qcontext['multi_website_companies_current'] = {'company_id': cur_company.id, 'name': cur_company.name}
                qcontext['multi_website_companies'] = [
                    {'company_id': comp.id, 'name': comp.name}
                    for comp in self.env.user.company_ids if comp != cur_company
                ]

            qcontext.update(dict(
                self._context.copy(),
                main_object=self,
                website=request.website,
                url_for=url_for,
                res_company=request.website.company_id.sudo(),
                default_lang_code=request.env['ir.http']._get_default_lang().code,
                languages=request.env['res.lang'].get_available(),
                translatable=translatable,
                editable=editable,
                # retrocompatibility, remove me in master
                menu_data={'children': []} if request.website.is_user() else None,
            ))

        return qcontext

    @api.model
    def get_default_lang_code(self):
        website_id = self.env.context.get('website_id')
        if website_id:
            lang_code = self.env['website'].browse(website_id).default_lang_id.code
            return lang_code
        else:
            return super(View, self).get_default_lang_code()

    def redirect_to_page_manager(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/website/pages',
            'target': 'self',
        }

    def _read_template_keys(self):
        return super(View, self)._read_template_keys() + ['website_id']

    @api.model
    def _save_oe_structure_hook(self):
        res = super(View, self)._save_oe_structure_hook()
        res['website_id'] = self.env['website'].get_current_website().id
        return res

    @api.model
    def _set_noupdate(self):
        '''If website is installed, any call to `save` from the frontend will
        actually write on the specific view (or create it if not exist yet).
        In that case, we don't want to flag the generic view as noupdate.
        '''
        if not self._context.get('website_id'):
            super(View, self)._set_noupdate()

    def save(self, value, xpath=None):
        self.ensure_one()
        current_website = self.env['website'].get_current_website()
        # xpath condition is important to be sure we are editing a view and not
        # a field as in that case `self` might not exist (check commit message)
        if xpath and self.key and current_website:
            # The first time a generic view is edited, if multiple editable parts
            # were edited at the same time, multiple call to this method will be
            # done but the first one may create a website specific view. So if there
            # already is a website specific view, we need to divert the super to it.
            website_specific_view = self.env['ir.ui.view'].search([
                ('key', '=', self.key),
                ('website_id', '=', current_website.id)
            ], limit=1)
            if website_specific_view:
                self = website_specific_view
        super(View, self).save(value, xpath=xpath)
