from openerp import api, models, fields

class Planner(models.Model):
    """Planner Model.
    Each Planner has link to an ir.ui.view record that is a template used
    to display the planner pages.
    Each Planner has link to ir.ui.menu record that is a top menu used to display the
    planner launcher(progressbar)

    Method _prepare_<planner_application>_data(self, cr, uid, context) that 
    generate the values used to display in specific planner pages
    """
    _name = 'planner.planner'

    name = fields.Char('Name', required=True)
    menu_id = fields.Many2one('ir.ui.menu', 'Menu', required=True)
    view_id = fields.Many2one('ir.ui.view', 'Template', required=True)
    progress = fields.Integer("Progress")
    data = fields.Text('Data')
    tooltip_planner = fields.Html('Planner Tooltips', translate=True)
    planner_application = fields.Char('Planner Application Name',
        required=True,
        help='Technical name of the planner modules') 

    @api.cr_uid_ids_context
    def render(self, cr, uid, template_id, planner_apps, context=None):
        values = {}
        #prepare the planner data as per the planner application 
        planner_find_method_name = '_prepare_%s_data' % planner_apps
        if hasattr(self, planner_find_method_name):
            values = getattr(self, planner_find_method_name)(cr, uid, context=context)
        html = self.pool['ir.ui.view'].render(cr, uid, template_id, values, context=context)
        return html

    @api.model
    def prepare_backend_url(self, action_id, view_type='list', module_name=None):
        action_id = self.env['ir.model.data'].xmlid_to_res_id(action_id) or ''
        module_id = ''
        if module_name:
            module_id = self.env['ir.module.module'].search([('name', '=', module_name)], limit=1).id or ''
        url = "/web#id="+str(module_id)+"&view_type="+view_type+"&action="+str(action_id)+""
        return url