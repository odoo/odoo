/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { CalendarController } from '@web/views/calendar/calendar_controller';
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';

import { serializeDate } from "@web/core/l10n/dates";

import { TimeOffCalendarFilterPanel } from './filter_panel/calendar_filter_panel';
import { TimeOffFormViewDialog } from '../view_dialog/form_view_dialog';
import { useLeaveCancelWizard } from '../hooks';

const { EventBus, useSubEnv } = owl;

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
            context['default_employee_id'] = this.employeeId;
        }
        if (this.model.meta.scale == 'day') {
            context['default_date_from'] = serializeDate(
                this.model.data.range.start.set({ hours: 7 }), "datetime"
            );
            context['default_date_to'] = serializeDate(
                this.model.data.range.end.set({ hours: 19 }), "datetime"
            );
        }

        this.displayDialog(FormViewDialog, {
            resModel: 'hr.leave',
            title: this.env._t('New Time Off'),
            viewId: this.model.formViewId,
            onRecordSaved: () => {
                this.model.load();
                this.env.timeOffBus.trigger('update_dashboard');
            },
            context: context,
        });
    }

    newAllocationRequest() {
        const context = {
            'form_view_ref': 'hr_holidays.hr_leave_allocation_view_form_dashboard',
        };
        if (this.employeeId) {
            context['default_employee_id'] = this.employeeId;
            context['default_employee_ids'] = [this.employeeId];
            context['form_view_ref'] = 'hr_holidays.hr_leave_allocation_view_form_manager_dashboard';
        }

        this.displayDialog(FormViewDialog, {
            resModel: 'hr.leave.allocation',
            title: this.env._t('New Allocation'),
            context: context,
        });
    }

    deleteRecord(record) {
        if (!record.can_cancel) {
            this.displayDialog(ConfirmationDialog, {
                title: this.env._t("Confirmation"),
                body: this.env._t("Are you sure you want to delete this record ?"),
                confirm: async () => {
                    await this.model.unlinkRecord(record.id);
                    this.env.timeOffBus.trigger('update_dashboard');
                },
                cancel: () => {},
            });
        } else {
            this.leaveCancelWizard(record.id, () => {
                this.model.load();
                this.env.timeOffBus.trigger('update_dashboard');
            });
        }
    }

    async editRecord(record, context = {}, shouldFetchFormViewId = true) {
        const onDialogClosed = () => {
            this.model.load();
            this.env.timeOffBus.trigger('update_dashboard');
        };

        return new Promise((resolve) => {
            this.displayDialog(
                TimeOffFormViewDialog, {
                    resModel: this.model.resModel,
                    resId: record.id || false,
                    context,
                    title: this.env._t("Time Off Request"),
                    viewId: this.model.formViewId,
                    onRecordSaved: onDialogClosed,
                    onRecordDeleted: (record) => this.deleteRecord(record),
                    onLeaveCancelled: onDialogClosed,
                },
                { onClose: () => resolve() }
            );
        });
    }
}
TimeOffCalendarController.template = "hr_holidays.CalendarController";
TimeOffCalendarController.components = {
    ...TimeOffCalendarController.components,
    FilterPanel: TimeOffCalendarFilterPanel,
}
