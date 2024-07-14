/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { DocumentsListController } from "@documents/views/list/documents_list_controller";
import { DocumentsSpreadsheetControllerMixin } from "../documents_spreadsheet_controller_mixin";

patch(DocumentsListController.prototype, DocumentsSpreadsheetControllerMixin());
