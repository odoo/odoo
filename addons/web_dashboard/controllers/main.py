from openerp import tools
from openerp.addons.web import http
from openerp.addons.web.http import request

class Dashboard(http.Controller):

    def get_users_list(self):
        users = request.env['res.users'].search([('login_date','=',False)]).sorted(key=lambda u: u.create_date, reverse=True)
        pending = users.filtered(lambda u:u.signup_valid)
        expired = users - pending
        return (pending, expired)

    @http.route('/dashboard/info', type='json', auth='user')
    def get_info(self, **kw):
        installed_apps = request.env['ir.module.module'].search_count([('application','=', True),('state','in',['installed', 'to upgrade', 'to remove'])])
        active_users = request.env['res.users'].search_count([('active','=', True),('login_date','!=',False)])
        pending, expired = self.get_users_list()
        users = {'expired':zip(expired.mapped('id'),expired.mapped('login')),'pending': zip(pending.mapped('id'),pending.mapped('login'))}
        panners = request.env['planner.planner'].search([])
        icp = request.env['ir.config_parameter']
        videos = {
            'twitter': int(icp.get_param('dashboard.twitter')),
            'facebook': int(icp.get_param('dashboard.facebook')),
            'linkedin': int(icp.get_param('dashboard.linkedin'))
        }
        template_user_id = icp.get_param('auth_signup.template_user_id')
        planner_data = {
            'planners': zip(panners.mapped('menu_id.name'),panners.mapped('progress'),panners.mapped('menu_id.id')),
            'overall_progress': round((sum(panners.mapped('progress')) * 1.0) / (len(panners.mapped('progress')) or 1), 2)
        }
        return {'installed_apps':installed_apps,'active_users':active_users,'users':users,'planner_data':planner_data,'videos':videos, 'template_user_id': template_user_id}

    @http.route('/dashboard/create_users', type='json', auth='user')
    def create_user(self, users, optional_message):
        context = request.context
        context['create_user'] = 1
        if optional_message:
            context['custom_message'] = optional_message
        user_obj = request.env['res.users'].with_context(context)
        emails_adderesses= users.strip().strip('\n').split('\n')
        if all([tools.single_email_re.match(email.strip()) != None for email in emails_adderesses ]):
            already_users = user_obj.search([('login','in',emails_adderesses),'|',('active','=',True),('active','=',False)])
            for user in already_users:
                if user.login_date == False and not user.signup_valid:
                    user.action_reset_password()
                else:
                    #Already a user activated in case it is deactivated
                    user.active = True
            new_users = set(emails_adderesses) - set(already_users.mapped('login'))
            for user in new_users:
                template_user_id = request.env['ir.config_parameter'].get_param('auth_signup.template_user_id', 'False')
                if template_user_id: 
                    user_obj.browse(int(template_user_id)).copy(default = {'login':user,'name':user,'email':user, 'active': True})
                else:
                    user_obj.create({'login':user,'name':user,'email':user})
            return {'has_error':False}
        else:
            return {'has_error':True, 'message': "Please!! Provide valid email ids"}

    @http.route('/dashboard/grant_videos', type='json', auth='user')
    def grant_videos(self, network):
        request.env['ir.config_parameter'].set_param(network,3)
        return {'has_error':False}





