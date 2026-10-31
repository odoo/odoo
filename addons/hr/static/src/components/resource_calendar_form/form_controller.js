/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

export class ResourceCalendarFormController extends FormController {
    setup() {
        super.setup();
        onWillStart(async () => {
            this.isHrUser = await user.hasGroup("hr.group_hr_user");
        });
    }

    getStaticActionMenuItems() {
        return {
            ...super.getStaticActionMenuItems(),
            clearEntries: {
                isAvailable: () => this.isHrUser && this.model.root.data.calendar_type === "variable",
                sequence: 20,
                icon: "event_busy",
                description: _t("Clear Entries"),
                callback: () =>
                    this.actionService.doAction("hr.hr_resource_calendar_clear_wizard_action", {
                        additionalContext: { default_calendar_id: this.model.root.resId },
                    }),
            },
        };
    }

    async onWillSaveRecord(record) {
        if (!record.resId) {
            return true;
        }
        const linked_employees_count = record.data.employees_count || 0;
        if (linked_employees_count > 1) {
            return new Promise((resolve) => {
                this.dialogService.add(ConfirmationDialog, {
                    title: _t("Confirmation Warning"),
                    body: _t(
                        "This working schedule is used by " +
                            linked_employees_count +
                            " employee(s), are you sure you want change it for all employees?"
                    ),
                    confirmLabel: _t("Confirm"),
                    confirm: () => resolve(true),
                    cancel: () => {
                        record.discard();
                        resolve(false);
                    },
                });
            });
        }

        return true;
    }
}

export const resourceCalendarFormView = {
    ...formView,
    Controller: ResourceCalendarFormController,
};

registry.category("views").add("resource_calendar_form", resourceCalendarFormView);
