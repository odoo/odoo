/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

export class ResourceCalendarFormController extends FormController {
    async onWillSaveRecord(record) {
        if (!record.resId) {
            return true;
        }
        const linked_employees_count = await this.orm.call(
            "resource.calendar",
            "get_number_of_linked_employees",
            [record.resId]
        );
        if (linked_employees_count > 0) {
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
