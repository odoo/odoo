/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class ExpenseLinesListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.threadService = useService("mail.thread");

        this.sheetId = this.env.model.root.resId;
        this.sheetThread = this.threadService.getThread('hr.expense.sheet', this.sheetId);
    }

    /** @override **/
    async onCellClicked(record, column, ev) {
        const attachmentChecksum = record.data.message_main_attachment_checksum;

        if (attachmentChecksum && this.sheetThread.mainAttachment?.checksum !== attachmentChecksum) {
            this.sheetThread.update({ mainAttachment: this.sheetThread.attachments.find((attachment) => attachment.checksum === attachmentChecksum) });
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
    relatedFields: [{ name: "message_main_attachment_checksum", type: "char" }],
    additionalClasses: ["o_field_many2many"],
};

registry.category("fields").add("expense_lines_widget", expenseLinesWidget);
