# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv


class AbstractReport(osv.AbstractModel):
    """Model used to embed old style reports"""
    _name = 'report.abstract_report'
    _template = None
    _wrapped_report_class = None

    def render_html(self, cr, uid, ids, data=None, context=None):
        context = dict(context or {})

        # If the key 'landscape' is present in data['form'], passing it into the context
        if data and data.get('form', {}).get('landscape'):
            context['landscape'] = True

        if context and context.get('active_ids'):
            # Browse the selected objects via their reference in context
            model = context.get('active_model') or context.get('model')
            objects_model = self.pool[model]
            objects = objects_model.browse(cr, uid, context['active_ids'], context=context)
        else:
            # If no context is set (for instance, during test execution), build one
            model = self.pool['report']._get_report_from_name(cr, uid, self._template).model
            objects_model = self.pool[model]
            objects = objects_model.browse(cr, uid, ids, context=context)
            context['active_model'] = model
            context['active_ids'] = ids

        # Generate the old style report
        wrapped_report = self._wrapped_report_class(cr, uid, '',  context=context)
        wrapped_report.set_context(objects, data, context['active_ids'])

        # Rendering self._template with the wrapped report instance localcontext as
        # rendering environment
        docargs = dict(wrapped_report.localcontext)
        if not docargs.get('lang'):
            docargs.pop('lang', False)
        docargs['docs'] = docargs.get('objects')

        # Used in template translation (see translate_doc method from report model)
        docargs['doc_ids'] = context['active_ids']
        docargs['doc_model'] = model

        return self.pool['report'].render(cr, uid, [], self._template, docargs, context=context)
