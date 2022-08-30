/** @odoo-module */

import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';

export class ProjectStopRecurrenceConfirmationDialog extends ConfirmationDialog {
    _continueRecurrence() {
        if (this.props.continueRecurrence) {
            this.props.continueRecurrence();
        }
        this.props.close();
    }
}
ProjectStopRecurrenceConfirmationDialog.template = 'project.ProjectStopRecurrenceConfirmationDialog';
ProjectStopRecurrenceConfirmationDialog.props.continueRecurrence = { type: Function, optional: true };
