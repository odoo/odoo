/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { DocumentsListModel } from "@documents/views/list/documents_list_model";
import { XLSX_MIME_TYPES } from "@documents_spreadsheet/helpers";

patch(DocumentsListModel.Record.prototype, {
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
