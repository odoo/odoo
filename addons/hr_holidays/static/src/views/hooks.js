/** @odoo-module */

import { useService } from "@web/core/utils/hooks";

const { useEnv } = owl;

export function useStressDays(props) {
    return (info) => {
        const date = luxon.DateTime.fromJSDate(info.date).toISODate();
        const stressDay = props.model.stressDays[date];
        if (stressDay) {
            info.el.classList.add('hr_stress_day_' + stressDay);
        }
    }
}

export function useLeaveCancelWizard() {
    const action = useService('action');
    const env = useEnv();

    return (leaveId, callback) => {
        action.doAction({
            name: env._t('Delete Confirmation'),
            type: "ir.actions.act_window",
            res_model: "hr.holidays.cancel.leave",
            target: "new",
            views: [[false, "form"]],
            context: {
                default_leave_id: leaveId,
            }
        }, {
            onClose: callback,
        });
    }
}
