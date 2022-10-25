/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class ProjectDeleteSubtasksConfirmationDialog extends ConfirmationDialog { /* Custom confirmation dialog when deleting a task with subtasks in project.task form view */
    setup() {
        super.setup();
    }
	_confirmWithSubtasks() {
        if(this.isConfirmedOrCancelled) {
            return;
        }
        this.isConfirmedOrCancelled = true;
        this.disableButtons();
        if (this.props.confirmWithSubtasks) {
            try {
                this.props.confirmWithSubtasks();
            } catch (e) {
                this.props.close();
                throw e;
            }
        }
        this.props.close();
    }
}
ProjectDeleteSubtasksConfirmationDialog.template = "project.ProjectDeleteSubtasksConfirmationDialog";
ProjectDeleteSubtasksConfirmationDialog.props = {
    close: Function,
    title: {
        validate: (m) => {
            return (
                typeof m === "string" || (typeof m === "object" && typeof m.toString === "function")
            );
        },
        optional: true,
    },
    body: String,
    confirm: { type: Function, optional: true },
    confirmLabel: { type: String, optional: true },
	confirmWithSubtasks: { type: Function, optional: true },
    confirmWithSubtasksLabel: { type: String, optional: true },
    cancel: { type: Function, optional: true },
    cancelLabel: { type: String, optional: true },
};
