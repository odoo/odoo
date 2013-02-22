from openerp.osv import osv

class res_users_gamification_group(osv.Model):
    """ Update of res.users class
        - if adding groups to an user, check gamification.goal.plan linked to 
        this group, and the user. This is done by overriding the write method.
    """
    _name = 'res.users'
    _inherit = ['res.users']

    def write(self, cr, uid, ids, vals, context=None):
        print("Overwrite res_users_gamification_group", ids)
        write_res = super(res_users_gamification_group, self).write(cr, uid, ids, vals, context=context)
        if vals.get('groups_id'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_group_ids = [command[1] for command in vals['groups_id'] if command[0] == 4]
            user_group_ids += [id for command in vals['groups_id'] if command[0] == 6 for id in command[2]]

            goal_plan_obj = self.pool.get('gamification.goal.plan')
            plan_ids = goal_plan_obj.search(cr, uid, [('autojoin_group_id', 'in', user_group_ids)], context=context)

            goal_plan_obj.plan_subscribe_users(cr, uid, plan_ids, ids, context=context)
        return write_res

class res_groups_gamification_group(osv.Model):
    """ Update of res.groups class
        - if adding users from a group, check gamification.goal.plan linked to 
        this group, and the user. This is done by overriding the write method.
    """
    _name = 'res.groups'
    _inherit = 'res.groups'

    def write(self, cr, uid, ids, vals, context=None):
        print("Overwrite res_groups_gamification_group", ids)
        write_res = super(res_groups_gamification_group, self).write(cr, uid, ids, vals, context=context)
        if vals.get('users'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_ids = [command[1] for command in vals['users'] if command[0] == 4]
            user_ids += [id for command in vals['users'] if command[0] == 6 for id in command[2]]

            goal_plan_obj = self.pool.get('gamification.goal.plan')
            plan_ids = goal_plan_obj.search(cr, uid, [('autojoin_group_id', 'in', ids)], context=context)

            goal_plan_obj.plan_subscribe_users(cr, uid, plan_ids, user_ids, context=context)
        return write_res
