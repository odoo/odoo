/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService, useOwnedDialogs } from "@web/core/utils/hooks";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { useComponent } from "@odoo/owl";
import { pyToJsLocale } from "@web/core/l10n/utils";

export function formatNumber(lang, number, maxDecimals = 2) {
    const userLang = pyToJsLocale(lang);

    const numberFormat = new Intl.NumberFormat(userLang, { maximumFractionDigits: maxDecimals });
    return numberFormat.format(number);
}

export function useMandatoryDays(props) {
    return (info) => {
        const date = luxon.DateTime.fromJSDate(info.date).toISODate();
        const mandatoryDay = props.model.mandatoryDays[date];
        if (mandatoryDay) {
            const dayNumberElTop = info.view.el.querySelector(
                `.fc-day-top[data-date="${info.el.dataset.date}"]`
            );
            const dayNumberEl = info.view.el.querySelector(
                `.fc-day[data-date="${info.el.dataset.date}"]`
            );
            if (dayNumberElTop) {
                dayNumberElTop.classList.add('hr_mandatory_day', `hr_mandatory_day_top_${mandatoryDay}`);
            }
            if (dayNumberEl) {
                dayNumberEl.classList.add('hr_mandatory_day',`hr_mandatory_day_${mandatoryDay}`);
            }
        }
        return props.model.mandatoryDays;
    };
}

export function useLeaveCancelWizard() {
    const action = useService("action");

    return (leaveId, callback) => {
        action.doAction(
            {
                name: _t("Delete Confirmation"),
                type: "ir.actions.act_window",
                res_model: "hr.holidays.cancel.leave",
                target: "new",
                views: [[false, "form"]],
                context: {
                    default_leave_id: leaveId,
                },
            },
            {
                onClose: callback,
            }
        );
    };
}

export function useNewAllocationRequest() {
    const addDialog = useOwnedDialogs();
    const component = useComponent();
    return async (employeeId, holidayStatusId) => {
        const context = {
            form_view_ref: "hr_holidays.hr_leave_allocation_view_form_dashboard",
            is_employee_allocation: true,
        };
        if (employeeId) {
            context["default_employee_id"] = employeeId;
            context["default_employee_ids"] = [employeeId];
            context["form_view_ref"] =
                "hr_holidays.hr_leave_allocation_view_form_manager_dashboard";
        }
        if (holidayStatusId) {
            context["default_holiday_status_id"] = holidayStatusId;
        }
        addDialog(FormViewDialog, {
            resModel: "hr.leave.allocation",
            title: _t("New Allocation"),
            context: context,
            onRecordSaved: () => {
                component.env.timeOffBus.trigger("update_dashboard");
            },
        });
    };
}
