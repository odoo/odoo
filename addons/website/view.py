# -*- coding: utf-8 -*-

from lxml import etree
from openerp.osv import osv, fields


class view(osv.osv):
    _inherit = "ir.ui.view"
    _columns = {
        'inherit_option_id': fields.many2one('ir.ui.view','Optional Inheritancy'),
        'inherited_option_ids': fields.one2many('ir.ui.view','inherit_option_id','Optional Inheritancies'),
    }

    # Returns all views (called and inherited) related to a view
    # Used by translation mechanism, SEO and optional templates
    def _views_get(self, cr, uid, view, options=True, context={}, root=True):
        if type(view) in (str, unicode):
            mod_obj = self.pool.get("ir.model.data")
            m, n = view.split('.')
            _, view = mod_obj.get_object_reference(cr, uid, m, n)
        if type(view) == int:
            view_obj = self.pool.get("ir.ui.view")
            view = view_obj.browse(cr, uid, view, context=context)
        while root and view.inherit_id:
            view = view.inherit_id

        result = [view]
        todo = view.inherit_children_ids
        if options:
            todo += filter(lambda x: not x.inherit_id, view.inherited_option_ids)
        for child_view in todo:
            result += self._views_get(cr, uid, child_view, options=options, context=context, root=False)
        node = etree.fromstring(view.arch)
        for child in node.xpath("//t[@t-call]"):
            result += self._views_get(cr, uid, child.get('t-call'), options=options, context=context)
        return result
