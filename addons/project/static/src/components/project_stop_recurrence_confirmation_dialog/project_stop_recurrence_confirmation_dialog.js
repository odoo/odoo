/** @odoo-module */

import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';

export class ProjectStopRecurrenceConfirmationDialog extends ConfirmationDialog {
    _addressRecurrence() {
        const targetOption = document.querySelector('.o_radio_input[name="targetOption"]:checked').id;
        this.props.addressRecurrence(targetOption);
        this.props.close();
    }
}
ProjectStopRecurrenceConfirmationDialog.template = 'project.ProjectStopRecurrenceConfirmationDialog';
ProjectStopRecurrenceConfirmationDialog.props = {
    ...ConfirmationDialog.props,
    addressRecurrence: { type: Function },
    mode: { type: String },
};
