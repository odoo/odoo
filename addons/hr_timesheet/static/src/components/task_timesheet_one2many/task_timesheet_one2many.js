/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import {
    ConfirmationDialog,
    deleteConfirmationMessage,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

async function confirmDeleteRecord(dialog, record, onDelete) {
    if (record.isNew) {
        return onDelete();
    }
    const confirmed = await new Promise((resolve) => {
        dialog.add(ConfirmationDialog, {
            body: deleteConfirmationMessage,
            confirmLabel: _t("Delete"),
            confirmClass: "btn-danger",
            confirm: () => resolve(true),
            cancel: () => resolve(false),
        });
    });
    if (confirmed) {
        return onDelete();
    }
}

class TaskTimesheetListRenderer extends ListRenderer {
    static recordRowTemplate = "hr_timesheet.TaskTimesheetListRenderer.RecordRow";

    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    async onDeleteRecord(record) {
        return confirmDeleteRecord(this.dialog, record, () => super.onDeleteRecord(record));
    }
}

class TaskTimesheetOne2ManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: TaskTimesheetListRenderer,
    };

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this._baseOnDelete = this.activeActions.onDelete;
    }

    get rendererProps() {
        const rendererProps = super.rendererProps;
        if (this.props.viewMode !== "kanban" || !this._baseOnDelete) {
            return rendererProps;
        }
        this.activeActions.onDelete = (record) =>
            confirmDeleteRecord(this.dialog, record, () => this._baseOnDelete(record));
        return rendererProps;
    }
}

const taskTimesheetOne2ManyField = {
    ...x2ManyField,
    component: TaskTimesheetOne2ManyField,
};

registry.category("fields").add("task_timesheet_one2many", taskTimesheetOne2ManyField);
