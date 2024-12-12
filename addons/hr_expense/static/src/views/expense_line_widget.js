import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { uniqueId } from "@web/core/utils/functions";
import { FileViewer } from "@web/core/file_viewer/file_viewer";

export class ExpenseLinesListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.store = useService("mail.store");

        this.sheetId = this.env.model.root.resId;
        this.sheetThread = this.store.Thread.insert({ model: "hr.expense.sheet", id: this.sheetId });
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

export class ExpenseLinesKanbanRecord extends KanbanRecord {

    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    /** @override **/
    async onGlobalClick(ev) {
        const expenseName = this.props.record.data.name;
        const attachments = await this.orm.call('hr.expense', 'get_expense_attachments', [this.props.record.resId]);
        const files = attachments.map((attachment, index) => ({
            isImage: true,
            isViewable: true,
            name: expenseName + ` (${index + 1})`,
            defaultSource: attachment,
            downloadUrl: attachment,
        }));
        const viewerId = uniqueId('web.file_viewer');

        if (files.length) {
            registry.category("main_components").add(viewerId, {
                Component: FileViewer,
                props: {
                    files: files,
                    startIndex: 0,
                    close: () => {
                        registry.category('main_components').remove(viewerId);
                    },
                },
            });
        }
        super.onGlobalClick(ev);
    }
}

export class ExpenseLinesKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: ExpenseLinesKanbanRecord,
    };
}

export class ExpenseLinesWidget extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: ExpenseLinesListRenderer,
        KanbanRenderer: ExpenseLinesKanbanRenderer,
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
    additionalClasses: ["o_field_many2many"],
};

registry.category("fields").add("expense_lines_widget", expenseLinesWidget);
