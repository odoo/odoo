/** @odoo-module */

import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';

export class StopRecurrenceConfirmationDialog extends ConfirmationDialog {
    _continueRecurrence() {
        if (this.props.continueRecurrence) {
            this.props.continueRecurrence();
        }
        this.props.close();
    }
}
StopRecurrenceConfirmationDialog.template = 'project.StopRecurrenceConfirmationDialog';
StopRecurrenceConfirmationDialog.props.continueRecurrence = { type: Function, optional: true };
