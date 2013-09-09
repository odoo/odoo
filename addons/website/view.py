# -*- coding: utf-8 -*-

from lxml import etree, html
from openerp.osv import osv, fields


class view(osv.osv):
    _inherit = "ir.ui.view"
    _columns = {
        'inherit_option_id': fields.many2one('ir.ui.view','Optional Inheritancy'),
        'inherited_option_ids': fields.one2many('ir.ui.view','inherit_option_id','Optional Inheritancies'),
        'page': fields.boolean("Whether this view is a web page template (complete)"),
    }
    _defaults = {
        'page': False,
    }

    # Returns all views (called and inherited) related to a view
    # Used by translation mechanism, SEO and optional templates
    def _views_get(self, cr, uid, view, options=True, context=None, root=True, stack_result=None):
        if  not context:
            context = {}
        if  not stack_result:
            stack_result = []

        def view_obj(view):
            if type(view) in (str, unicode):
                mod_obj = self.pool.get("ir.model.data")
                m, n = view.split('.')
                _, view = mod_obj.get_object_reference(cr, uid, m, n)
            if type(view) == int:
                view_obj = self.pool.get("ir.ui.view")
                view = view_obj.browse(cr, uid, view, context=context)
            return view
        view = view_obj(view)

        while root and view.inherit_id:
            view = view.inherit_id

        result = [view]
        todo = view.inherit_children_ids
        if options:
            todo += filter(lambda x: not x.inherit_id, view.inherited_option_ids)
        for child_view in todo:
            result += self._views_get(cr, uid, child_view, options=options, context=context, root=False, stack_result=result)
        node = etree.fromstring(view.arch)
        for child in node.xpath("//t[@t-call]"):
            call_view = view_obj(child.get('t-call'))
            if call_view not in stack_result:
                result += self._views_get(cr, uid, call_view, options=options, context=context, stack_result=result)
        return result

    def save(self, cr, uid, model, res_id, field, value, xpath=None, context=None):
        """ Update the content of a field

        :param str model:
        :param int res_id:
        :param str xpath: valid xpath to the tag to replace
        """
        model_obj = self.pool.get(model)
        if xpath:
            origin = model_obj.read(cr, uid, [res_id], [field], context=context)[0][field]
            origin_tree = etree.fromstring(origin.encode('utf-8'))
            zone = origin_tree.xpath(xpath)[0]
            zone.getparent().replace(zone, html.fromstring(value))
            value = etree.tostring(origin_tree, encoding='utf-8')

        model_obj.write(cr, uid, res_id, {field: value}, context=context)
