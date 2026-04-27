/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import DocumentViewer from '@mrp_workorder/components/viewer';

export class MrpWorksheetDialog extends ConfirmationDialog {
    static props = {
        ...ConfirmationDialog.props,
        body: { optional: true },
        worksheetData: [Object, Boolean],
        worksheetText: Object,
    };
    static template = "mrp_workorder.MrpWorksheetDialog";
    static components = {
        ...ConfirmationDialog.components,
        DocumentViewer,
    };
}
