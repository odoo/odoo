from openerp.osv import osv


class res_users_employee_group(osv.Model):
    """ Update of res.users class
        - if adding groups to an user, check if base.group_user is in it
        (member of 'Employee'), create an employee form linked to it.
    """
    _name = 'res.users'
    _inherit = ['res.users']

    def write(self, cr, uid, ids, vals, context=None):
        write_res = super(res_users_employee_group, self).write(cr, uid, ids, vals, context=context)
        if vals.get('groups_id'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_group_ids = [command[1] for command in vals['groups_id'] if command[0] == 4]
            user_group_ids += [id for command in vals['groups_id'] if command[0] == 6 for id in command[2]]

            (model, group_id) = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'group_user')
            emp_obj = self.pool.get('hr.employee')
            if group_id in user_group_ids:
                # base.group_user in it, checking users
                for user in self.browse(cr, uid, ids, context=context):
                    if len(emp_obj.search(cr, uid, [('user_id', '=', user.id)], context=context)) == 0:
                        # no employee already linked to this user, create it
                        emp_obj.create(cr, uid, {
                            'user_id': user.id,
                            'name': user.name,
                            'image': user.image,
                        }, context=context)
        return write_res


class res_groups_employee_group(osv.Model):
    """ Update of res.groups class
        - if adding users to a group, check if base.group_user and if the case,
        create a employee profile
    """
    _name = 'res.groups'
    _inherit = 'res.groups'

    def write(self, cr, uid, ids, vals, context=None):
        write_res = super(res_groups_employee_group, self).write(cr, uid, ids, vals, context=context)
        (model, group_id) = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'group_user')

        # check adding users to base.group_user
        if vals.get('users') and group_id in ids:
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_ids = [command[1] for command in vals['users'] if command[0] == 4]
            user_ids += [id for command in vals['users'] if command[0] == 6 for id in command[2]]

            emp_obj = self.pool.get('hr.employee')
            for user_id in user_ids:
                if len(emp_obj.search(cr, uid, [('user_id', '=', user_id)], context=context)) == 0:
                    # no employee already linked to this user, create it
                    user = self.pool.get('res.users').browse(cr, uid, [user_id], context=context)
                    emp_obj.create(cr, uid, {
                        'user_id': user.id,
                        'name': user.name,
                        'image': user.image,
                    }, context=context)
        return write_res
