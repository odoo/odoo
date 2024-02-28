/** @odoo-module */

import session from 'web.session'
import { useService } from "@web/core/utils/hooks";
import { useEnv } from "@odoo/owl";

/**
 * Redirect to the sub employee kanban view.
 *
 * @private
 * @param {MouseEvent} event
 * @returns {Promise} action loaded
 *
 */
export function onEmployeeSubRedirect() {
    const actionService = useService('action');
    const orm = useService('orm');
    const rpc = useService('rpc');
    const env = useEnv();

    return async (event) => {
        const employeeId = parseInt(event.currentTarget.dataset.employeeId);
        if (!employeeId) {
            return {};
        }
        const type = event.currentTarget.dataset.type || 'direct';
        // Get subordonates of an employee through a rpc call.
        const subordinateIds = await rpc('/hr/get_subordinates', {
            employee_id: employeeId,
            subordinates_type: type,
            context: session.user_context
        });
        let action = await orm.call('hr.employee', 'get_formview_action', [employeeId]);
        action = {...action,
            name: env._t('Team'),
            view_mode: 'kanban,list,form',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            domain: [['id', 'in', subordinateIds]],
            res_id: false,
            context: {
                default_parent_id: employeeId,
            }
        };
        actionService.doAction(action);
    };
}
