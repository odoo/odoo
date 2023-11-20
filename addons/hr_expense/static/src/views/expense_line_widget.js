/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class ExpenseLinesListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.threadService = useService("mail.thread");
    }

    /** @override **/
    async onCellClicked(record, column, ev) {
        const sheetId = this.env.model.root.resId;
        const sheetThread = this.threadService.getThread('hr.expense.sheet', sheetId);
        const attachmentId = record.data.message_main_attachment_id[0]

        if (attachmentId) {
            sheetThread.update({ mainAttachment: sheetThread.attachments.find((attachment) => attachment.id === attachmentId) });
        }
        super.onCellClicked(record, column, ev);
    }
}

export class ExpenseLinesWidget extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: ExpenseLinesListRenderer,
    };

    setup() {
        super.setup();
        this.canOpenRecord = false;
    }

    get isMany2Many() {
        // The field is used like a many2many to allow for adding existing lines to the sheet.
        return true;
    }
}

export const expenseLinesWidget = {
    ...x2ManyField,
    component: ExpenseLinesWidget,
};

registry.category("fields").add("expense_lines_widget", expenseLinesWidget);
