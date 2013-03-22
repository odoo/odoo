from openerp.osv import osv


class res_users_gamification_group(osv.Model):
    """ Update of res.users class
        - if adding groups to an user, check gamification.goal.plan linked to
        this group, and the user. This is done by overriding the write method.
    """
    _name = 'res.users'
    _inherit = ['res.users']

    def write(self, cr, uid, ids, vals, context=None):
        write_res = super(res_users_gamification_group, self).write(cr, uid, ids, vals, context=context)
        if vals.get('groups_id'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_group_ids = [command[1] for command in vals['groups_id'] if command[0] == 4]
            user_group_ids += [id for command in vals['groups_id'] if command[0] == 6 for id in command[2]]

            goal_plan_obj = self.pool.get('gamification.goal.plan')
            plan_ids = goal_plan_obj.search(cr, uid, [('autojoin_group_id', 'in', user_group_ids)], context=context)

            goal_plan_obj.plan_subscribe_users(cr, uid, plan_ids, ids, context=context)
        return write_res

    def get_goals_todo_info(self, cr, uid, context=None):
        """Return the list of goals assigned to the user, grouped by plan"""
        goals_info = []
        goal_obj = self.pool.get('gamification.goal')
        plan_obj = self.pool.get('gamification.goal.plan')
        plan_ids = plan_obj.search(cr, uid, [('user_ids', 'in', uid)], context=context)
        for plan in plan_obj.browse(cr, uid, plan_ids, context=context):
            vals = {'name': plan.name, 'goals': []}

            goal_ids = goal_obj.search(cr, uid, [('user_id', '=', uid), ('plan_id', '=', plan.id)], context=context)
            all_done = True
            for goal in goal_obj.browse(cr, uid, goal_ids, context=context):
                if goal.last_update and goal.end_date and goal.last_update > goal.end_date:
                    # do not include goals of previous plan run
                    continue

                if goal.state == 'inprogress' or goal.state == 'inprogress_update':
                    all_done = False

                vals['goals'].append({
                    'id': goal.id,
                    'type_name': goal.type_id.name,
                    'type_condition': goal.type_id.condition,
                    'type_description': goal.type_description,
                    'state': goal.state,
                    'completeness': goal.completeness,
                    'computation_mode': goal.computation_mode,
                    'current': goal.current,
                    'target_goal': goal.target_goal,
                })
            # skip plans where all goal are done or failed
            if not all_done:
                goals_info.append(vals)
        return goals_info


class res_groups_gamification_group(osv.Model):
    """ Update of res.groups class
        - if adding users from a group, check gamification.goal.plan linked to
        this group, and the user. This is done by overriding the write method.
    """
    _name = 'res.groups'
    _inherit = 'res.groups'

    def write(self, cr, uid, ids, vals, context=None):
        write_res = super(res_groups_gamification_group, self).write(cr, uid, ids, vals, context=context)
        if vals.get('users'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_ids = [command[1] for command in vals['users'] if command[0] == 4]
            user_ids += [id for command in vals['users'] if command[0] == 6 for id in command[2]]

            goal_plan_obj = self.pool.get('gamification.goal.plan')
            plan_ids = goal_plan_obj.search(cr, uid, [('autojoin_group_id', 'in', ids)], context=context)

            goal_plan_obj.plan_subscribe_users(cr, uid, plan_ids, user_ids, context=context)
        return write_res
