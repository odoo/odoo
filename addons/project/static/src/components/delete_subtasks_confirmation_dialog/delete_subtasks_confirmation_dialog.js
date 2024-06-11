/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class DeleteSubtasksConfirmationDialog extends ConfirmationDialog {}

DeleteSubtasksConfirmationDialog.props = {
    ...ConfirmationDialog.props,
    body: { String, optional: true },
}

DeleteSubtasksConfirmationDialog.defaultProps = {
    ...ConfirmationDialog.defaultProps,
    body: _t("Deleting a task will also delete its associated sub-tasks. If you wish to preserve the sub-tasks, make sure to unlink them from their parent task beforehand. Are you sure you want to proceed?"),
    confirmLabel: _t("Delete"),
    cancel: () => {},
};
