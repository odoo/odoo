/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { DocumentsActivityModel } from "@documents/views/activity/documents_activity_model";

import { XLSX_MIME_TYPE } from "@documents_spreadsheet/helpers";

patch(DocumentsActivityModel.Record.prototype, {
    /**
     * @override
     */
    isViewable() {
        return (
            ["spreadsheet", "frozen_spreadsheet"].includes(this.data.handler) ||
            this.data.mimetype === XLSX_MIME_TYPE ||
            super.isViewable(...arguments)
        );
    },
});
