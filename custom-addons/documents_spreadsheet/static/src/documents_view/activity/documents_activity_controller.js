/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { DocumentsActivityController } from "@documents/views/activity/documents_activity_controller";
import { DocumentsSpreadsheetControllerMixin } from "../documents_spreadsheet_controller_mixin";

patch(DocumentsActivityController.prototype, DocumentsSpreadsheetControllerMixin());

patch(DocumentsActivityController.prototype, {
    /**
     * Prevents spreadsheets from being in the viewable attachments list
     * when previewing a file in the activity view.
     *
     * @override
     */
    isRecordPreviewable(record) {
        return super.isRecordPreviewable(...arguments) && record.data.handler !== "spreadsheet";
    },
});
