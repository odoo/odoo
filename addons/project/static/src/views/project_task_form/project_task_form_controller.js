/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { AddressRecurrenceConfirmationDialog } from "../../components/address_recurrence_confirmation_dialog/address_recurrence_confirmation_dialog";
import { AddressParentRecurrenceConfirmationDialog } from "../../components/address_parent_recurrence_confirmation_dialog/address_parent_recurrence_confirmation_dialog";

export class ProjectTaskFormController extends FormController {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.state.recurrenceUpdate = "this";
    }

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        const task = this.model.root;
        if (task.data.recurrence_id) {
            menuItems.archive.callback = () => this.addressRecurrence("archive", () => task.archive());
        } else if (task.data.recurrence_template_id) {
            menuItems.archive.callback = () => this.addressParentRecurrence("archive", () => task.archive());
        }
        return menuItems;
    }

    async deleteRecord() {
        const task = this.model.root;
        const callback = async () => {
            await task.delete();
            if (!task.resId) {
                this.env.config.historyBack();
            }
        }
        if (task.data.recurrence_id) {
            this.addressRecurrence("delete", callback);
        } else if (task.data.recurrence_template_id) {
            this.addressParentRecurrence("delete", callback);
        } else {
            await super.deleteRecord(...arguments);
        }
    }

    async addressRecurrence(mode, callback) {
        this.dialog.add(AddressRecurrenceConfirmationDialog, {
            confirm: async () => {
                if (this.state.recurrenceUpdate === "future") {
                    const task = this.model.root;
                    await this.orm.call(
                        task.resModel,
                        "action_unlink_recurrence",
                        [task.resId],
                    );
                }
                callback();
            },
            onChangeRecurrenceUpdate: (recurrenceUpdate) => {
                this.state.recurrenceUpdate = recurrenceUpdate;
            },
            mode: mode,
        });
    }

    async addressParentRecurrence(mode, callback) {
        this.dialog.add(AddressParentRecurrenceConfirmationDialog, {
            confirm: async () => {
                if (this.state.recurrenceUpdate === "future") {
                    const task = this.model.root;
                    await this.orm.call(
                        task.resModel,
                        "action_unlink_task_from_recurrence",
                        [task.resId],
                    );
                }
                callback();
            },
            onChangeRecurrenceUpdate: (recurrenceUpdate) => {
                this.state.recurrenceUpdate = recurrenceUpdate;
            },
            mode: mode,
        });
    }
}
