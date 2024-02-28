/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

const { useComponent, useEnv } = owl;

export function useArchiveEmployee() {
    const component = useComponent();
    const env = useEnv();
    const action = useService("action");
    return (id) => {
        action.doAction({
            type: 'ir.actions.act_window',
            name: env._t('Employee Termination'),
            res_model: 'hr.departure.wizard',
            views: [[false, 'form']],
            view_mode: 'form',
            target: 'new',
            context: {
                'active_id': id,
                'toggle_active': true,
            }
        }, {
            onClose: async () => {
                await component.model.load();
                component.model.notify();
            },
        });
    }
}
