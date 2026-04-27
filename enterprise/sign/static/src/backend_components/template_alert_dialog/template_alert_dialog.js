/** @odoo-module **/

import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class TemplateAlertDialog extends AlertDialog {
    static props = {
        ...AlertDialog.props,
        body: { type: String, optional: true },
        failedTemplates: { type: Array },
        successTemplateCount: { type: Number, optional: true },
    };
    static defaultProps = {
        ...ConfirmationDialog.defaultProps,
        ...AlertDialog.defaultProps,
    };
    static template = "sign.TemplateAlertDialog";
}
