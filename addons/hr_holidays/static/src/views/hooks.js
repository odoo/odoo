/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export function useMandatoryDays(props) {
    return (info) => {
        const date = luxon.DateTime.fromJSDate(info.date).toISODate();
        const mandatoryDay = props.model.mandatoryDays[date];
        if (mandatoryDay) {
            const dayNumberElTop = info.view.el.querySelector(`.fc-day-top[data-date="${info.el.dataset.date }"]`)
            const dayNumberEl = info.view.el.querySelector(`.fc-day[data-date="${info.el.dataset.date }"]`)
            if (dayNumberElTop) {
                dayNumberElTop.classList.add(`hr_mandatory_day_top_${mandatoryDay}`);
            }
            if (dayNumberEl) {
                dayNumberEl.classList.add(`hr_mandatory_day_${mandatoryDay}`);
            }
        }
        return props.model.mandatoryDays;
    }
}

export function useLeaveCancelWizard() {
    const action = useService('action');

    return (leaveId, callback) => {
        action.doAction({
            name: _t('Delete Confirmation'),
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
