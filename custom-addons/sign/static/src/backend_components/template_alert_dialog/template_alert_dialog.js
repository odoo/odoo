/** @odoo-module **/

import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class TemplateAlertDialog extends AlertDialog {}
TemplateAlertDialog.props = {
    ...AlertDialog.props,
    body: { type: String, optional: true },
    failedTemplates: { type: Array },
    successTemplateCount: { type: Number, optional: true },
};
TemplateAlertDialog.defaultProps = {
    ...ConfirmationDialog.defaultProps,
    ...AlertDialog.defaultProps,
};
TemplateAlertDialog.template = "sign.TemplateAlertDialog";
