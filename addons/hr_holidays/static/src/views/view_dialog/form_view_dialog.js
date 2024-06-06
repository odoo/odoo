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
        const record = this.model.root.data

        this.props.onRecordDeleted(record)
        this.props.onCancelLeave();
        if (record.can_cancel) {
            this.leaveCancelWizard(record.id, () => {
                this.props.onLeaveCancelled();
            });
        }
    }

    get canDelete() {
        const record = this.model.root.data;
        return !this.model.root.isNew && (record.can_cancel || record.state && ['confirm', 'validate', 'validate1'].includes(record.state));
    }
}

TimeOffDialogFormController.props = {
    ...FormController.props,
    onCancelLeave: Function,
    onRecordDeleted: Function,
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
            onRecordDeleted: (record) => {
                this.props.onRecordDeleted(record)
            },
            onLeaveCancelled: this.props.onLeaveCancelled.bind(this),
        })
    }
}
TimeOffFormViewDialog.props = {
    ...TimeOffFormViewDialog.props,
    onRecordDeleted: Function,
    onLeaveCancelled: Function,
}
