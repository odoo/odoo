import { useSubEnv } from "@web/owl2/utils";
import { _t } from "@web/core/l10n/translation";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { userHasEmployeeInCurrentCompany } from "@hr_holidays/utils";

import { serializeDate } from "@web/core/l10n/dates";

import { TimeOffCalendarSidePanel } from "./calendar_side_panel/calendar_side_panel";
import { TimeOffCalendarMobileFilterPanel } from "./calendar_filter_panel/calendar_mobile_filter_panel";
import { TimeOffNewDropdown } from "../../components/time_off_new_dropdown/time_off_new_dropdown";
import { TimeOffFormViewDialog } from "../view_dialog/form_view_dialog";
import { useLeaveCancelWizard, useNewAllocationRequest } from "../hooks";
import { EventBus, onWillStart } from "@odoo/owl";

export class TimeOffCalendarController extends CalendarController {
    static components = {
        ...CalendarController.components,
        CalendarSidePanel: TimeOffCalendarSidePanel,
        MobileFilterPanel: TimeOffCalendarMobileFilterPanel,
        NewButton: TimeOffNewDropdown,
    };
    static template = "hr_holidays.CalendarController";
    setup() {
        super.setup();
        useSubEnv({
            timeOffBus: new EventBus(),
        });
        this.leaveCancelWizard = useLeaveCancelWizard();
        this.newAllocRequest = useNewAllocationRequest();

        onWillStart(async () => {
            this.hasEmployee = await userHasEmployeeInCurrentCompany(this.orm);
            if (!this.employeeId && !this.hasEmployee) {
                this.env.services.notification.add(
                    _t("You are not linked to an employee in the current company, so you cannot create requests for yourself."),
                    { type: "warning", sticky: true }
                );
            }
        });
    }

    get employeeId() {
        return this.model.employeeId;
    }

    newTimeOffRequest() {
        if (!this.employeeId && !this.hasEmployee) {
            this.displayDialog(AlertDialog, {
                title: _t("UserError"),
                body: _t("This operation is not allowed as you are not linked to an employee in the current company."),
            });
            return;
        }
        const context = {};
        if (this.props.context.active_id && this.props.context.active_model === "hr.employee") {
            context["default_employee_id"] = this.props.context.active_id;
        } else if (this.employeeId) {
            context["default_employee_id"] = this.employeeId;
        }
        if (this.model.meta.scale == "day") {
            context["default_date_from"] = serializeDate(
                this.model.data.range.start.set({ hours: 7 }),
                "datetime"
            );
            context["default_date_to"] = serializeDate(
                this.model.data.range.end.set({ hours: 19 }),
                "datetime"
            );
        }

        this.displayDialog(TimeOffFormViewDialog, {
            resModel: "hr.leave",
            title: _t("New Time Off"),
            viewId: this.model.formViewId,
            onRecordSaved: () => {
                this.model.load();
                this.env.timeOffBus.trigger("update_dashboard");
            },
            onRecordDeleted: (record) => {},
            onLeaveCancelled: (record) => {},
            size: "md",
            context: context,
        });
    }

    newAllocationRequest() {
        if (!this.employeeId && !this.hasEmployee) {
            this.displayDialog(AlertDialog, {
                title: _t("UserError"),
                body: _t("This operation is not allowed as you are not linked to an employee in the current company."),
            });
            return;
        }
        let empId;
        if (this.props.context.active_id && this.props.context.active_model === "hr.employee") {
            empId = this.props.context.active_id;
        } else if (this.employeeId) {
            empId = this.employeeId;
        }
        this.newAllocRequest({ employeeId: empId, forceLargeDialog: this.props.context.hide_employee_name ?? false })
    }

    _deleteRecord(resId, canCancel) {
        if (!canCancel) {
            this.displayDialog(ConfirmationDialog, {
                title: _t("Confirmation"),
                body: _t("Are you sure you want to delete this record?"),
                confirm: async () => {
                    await this.model.unlinkRecord(resId);
                    this.env.timeOffBus.trigger("update_dashboard");
                },
                cancel: () => {},
            });
        } else {
            this.leaveCancelWizard(resId, () => {
                this.model.load();
                this.env.timeOffBus.trigger("update_dashboard");
            });
        }
    }

    deleteRecord(record) {
        this._deleteRecord(record.id, record.rawRecord.can_cancel);
    }

    _editRecord(record, context, props = {}) {
        if (!this.employeeId && !this.hasEmployee) {
            this.displayDialog(AlertDialog, {
                title: _t("UserError"),
                body: _t("This operation is not allowed as you are not linked to an employee in the current company."),
            });
            return;
        }
        const onDialogClosed = () => {
            this.model.load();
            this.env.timeOffBus.trigger("update_dashboard");
        };

        return new Promise((resolve) => {
            this.displayDialog(
                TimeOffFormViewDialog,
                {
                    ...props,
                    resModel: this.model.resModel,
                    resId: record.id || false,
                    context,
                    title: _t("Time Off Request"),
                    viewId: this.model.formViewId,
                    onRecordSaved: onDialogClosed,
                    onRecordDeleted: (record) =>
                        this._deleteRecord(record.resId, record.data.can_cancel),
                    onLeaveCancelled: onDialogClosed,
                    size: "md",
                },
                { onClose: () => resolve() }
            );
        });
    }

    async editRecord(record, context = {}) {
        return this._editRecord(record, context);
    }
}

export class TimeOffReportCalendarController extends TimeOffCalendarController {
    async editRecord(record, context = {}) {
        return this._editRecord(record, context, { canExpand: false });
    }
}
