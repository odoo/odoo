/** @odoo-module */

import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

import { registry } from '@web/core/registry';

import { formView } from '@web/views/form/form_view';
import { FormController } from '@web/views/form/form_controller';

import { useLeaveCancelWizard } from '../hooks';

export class TimeOffDialogFormController extends FormController {
    setup() {
        super.setup();
        this.leaveCancelWizard = useLeaveCancelWizard();
    }

    deleteRecord() {
        const leaveId = this.model.root.data.id;

        this.props.onCancelLeave();
        if (this.model.root.data.can_cancel) {
            this.leaveCancelWizard(leaveId, () => {
                this.props.onLeaveCancelled();
            });
        }
    }

    get canDelete() {
        return this.model.root.data.can_cancel || false;
    }
}

TimeOffDialogFormController.props = {
    ...FormController.props,
    onCancelLeave: Function,
    onLeaveCancelled: Function,
}

registry.category('views').add('timeoff_dialog_form', {
    ...formView,
    Controller: TimeOffDialogFormController,
});


export class TimeOffFormViewDialog extends FormViewDialog {
    setup() {
        super.setup();

        this.viewProps = Object.assign(this.viewProps, {
            type: "timeoff_dialog_form",
            buttonTemplate: 'hr_holidays.FormViewDialog.buttons',
            onCancelLeave: () => {
                this.props.close();
            },
            onLeaveCancelled: this.props.onLeaveCancelled.bind(this),
        })
    }
}
TimeOffFormViewDialog.props = {
    ...TimeOffFormViewDialog.props,
    onLeaveCancelled: Function,
}
