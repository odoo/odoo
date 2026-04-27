/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { DocumentsActivityController } from "@documents/views/activity/documents_activity_controller";
import { DocumentsSpreadsheetControllerMixin } from "../documents_spreadsheet_controller_mixin";

patch(DocumentsActivityController.prototype, DocumentsSpreadsheetControllerMixin());
