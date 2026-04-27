/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { DocumentsKanbanRecord } from "@documents/views/kanban/documents_kanban_model";

import { XLSX_MIME_TYPES } from "@documents_spreadsheet/helpers";

patch(DocumentsKanbanRecord.prototype, {
    /**
     * @override
     */
    isViewable() {
        return (
            ["spreadsheet", "frozen_spreadsheet"].includes(this.data.handler) ||
            XLSX_MIME_TYPES.includes(this.data.mimetype) ||
            super.isViewable(...arguments)
        );
    },
});
