/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { Dropdown, DropdownItem } from "@web/core/dropdown/dropdown";

import { serializeDate } from "@web/core/l10n/dates";

import { TimeOffCalendarFilterPanel } from "./filter_panel/calendar_filter_panel";
import { TimeOffFormViewDialog } from "../view_dialog/form_view_dialog";
import { useLeaveCancelWizard } from "../hooks";
import { EventBus, useSubEnv } from "@odoo/owl";

export class TimeOffCalendarController extends CalendarController {
    setup() {
        super.setup();
        useSubEnv({
            timeOffBus: new EventBus(),
        });
        this.leaveCancelWizard = useLeaveCancelWizard();
    }

    get employeeId() {
        return this.model.employeeId;
    }

    get filterPanelProps() {
        return {
            ...super.filterPanelProps,
            employee_id: this.employeeId,
        };
    }

    newTimeOffRequest() {
        const context = {};
        if (this.employeeId) {
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

        this.displayDialog(FormViewDialog, {
            resModel: "hr.leave",
            title: _t("New Time Off"),
            viewId: this.model.formViewId,
            onRecordSaved: () => {
                this.model.load();
                this.env.timeOffBus.trigger("update_dashboard");
            },
            context: context,
        });
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

    async editRecord(record, context = {}, shouldFetchFormViewId = true) {
        const onDialogClosed = () => {
            this.model.load();
            this.env.timeOffBus.trigger("update_dashboard");
        };

        return new Promise((resolve) => {
            this.displayDialog(
                TimeOffFormViewDialog,
                {
                    resModel: this.model.resModel,
                    resId: record.id || false,
                    context,
                    title: _t("Time Off Request"),
                    viewId: this.model.formViewId,
                    onRecordSaved: onDialogClosed,
                    onRecordDeleted: (record) => this._deleteRecord(record.resId, record.data.can_cancel),
                    onLeaveCancelled: onDialogClosed,
                    size: "md",
                },
                { onClose: () => resolve() }
            );
        });
    }
}
TimeOffCalendarController.components = {
    ...TimeOffCalendarController.components,
    Dropdown,
    DropdownItem,
    FilterPanel: TimeOffCalendarFilterPanel,
};

TimeOffCalendarController.template = "hr_holidays.CalendarController";
