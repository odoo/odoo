# -*- coding: utf-8 -*-
"""
Website-context rendering needs to add some metadata to rendered fields,
as well as render a few fields differently.

Also, adds methods to convert values back to openerp models.
"""


from openerp.addons.base.ir.ir_qweb import QWebContext
from openerp.osv import osv, orm, fields


class QWeb(orm.AbstractModel):
    """ QWeb object for rendering stuff in the website context
    """
    _inherit = 'website.qweb'

    def render(self, cr, uid, id_or_xml_id, qwebcontext=None, loader=None, context=None):
        if qwebcontext is None:
            qwebcontext = {}

        if not isinstance(qwebcontext, QWebContext):
            qwebcontext = QWebContext(cr, uid, qwebcontext, loader=loader, context=context)


        context = context or qwebcontext.context          
        website_id=context.get('website_id')

        if website_id:
            if 'experiment_id' in context:
                page_id = self.pool["website_version.experiment_page"].search(cr, uid, [('key', '=', id_or_xml_id),('experiment_id.state','=','running'),('experiment_id.website_id.id','=',website_id)], context=context)
                if page_id:
                    RNG_exp = int(context.get('RNG_exp'))
                    number_id = int(''.join(str(ord(c)) for c in id_or_xml_id))

                    page = self.pool["website_version.experiment_page"].browse(cr, uid, [page_id[0]], context=context)
                    exp = page.experiment_id
                    result=[]
                    pond_sum=0
                    for page in exp.experiment_page_ids:
                        if page.key == id_or_xml_id:
                            result.append([page.ponderation+pond_sum, page.snapshot_id.id])
                            pond_sum+=page.ponderation
                    if pond_sum:
                        #RANDOM
                        x = (RNG_exp+number_id)*179426549%pond_sum
                        for res in result:
                            if x<res[0]:
                                context['snapshot_id'] = res[1]
                                break

            if 'snapshot_id' in context:
                snapshot_id=context.get('snapshot_id')
                id_or_xml_id=self.pool["ir.ui.view"].search(cr, uid, [('key', '=', id_or_xml_id), '|', ('snapshot_id', '=', False), ('snapshot_id', '=', snapshot_id), '|',('website_id','=',website_id),('website_id','=',False)], order='website_id, snapshot_id', limit=1, context=context)[0]
            else:
                id_or_xml_id=self.pool["ir.ui.view"].search(cr, uid, [('key', '=', id_or_xml_id), '|', ('website_id','=',website_id),('website_id','=',False),('snapshot_id', '=', False)], order='website_id', limit=1, context=context)[0]

            

        qwebcontext['__template__'] = id_or_xml_id
        stack = qwebcontext.get('__stack__', [])
        if stack:
            qwebcontext['__caller__'] = stack[-1]
        stack.append(id_or_xml_id)
        qwebcontext['__stack__'] = stack
        qwebcontext['xmlid'] = str(stack[0]) # Temporary fix
        return self.render_node(self.get_template(id_or_xml_id, qwebcontext), qwebcontext)


        