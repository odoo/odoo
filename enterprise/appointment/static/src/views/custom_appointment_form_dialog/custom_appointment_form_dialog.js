/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { FormController } from '@web/views/form/form_controller';
import { formView } from '@web/views/form/form_view';
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';
import { useService } from "@web/core/utils/hooks";
import { registry } from '@web/core/registry';


/**
 * This custom Form Dialog (Controller) is used to customize 'custom'
 * appointment types created with slot selection on the calendar view.
 * Using "Select Dates" then using "Configure" button will open a small
 * form in a dialog allowing to customize the created appointment type.
 * This controller is used to handle actions on that form: saving the
 * form and copying the invitation link, and redirecting to full form view.
 */
export class CustomAppointmentFormController extends FormController {
    static props = {
        ...FormController.props,
        inviteUrl: String,
        onLinkCopied: Function,
    };

    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
    }

    /**
    * Deprecated: remove me in master.
    */
    async onClickMoreOptions() {
        if (await super.saveButtonClicked()) {
            this.actionService.doAction({
                name: _t('Open Appointment Type Form'),
                type: 'ir.actions.act_window',
                res_model: 'appointment.type',
                views: [[false, 'form']],
                res_id: this.model.root.resId,
            });
        }
    }

    async onClickSaveAndCopy() {
        if (await super.saveButtonClicked()) {
            setTimeout(async () => await navigator.clipboard.writeText(this.props.inviteUrl));
            this.props.onLinkCopied();
        }
    }
}

export class CustomAppointmentFormViewDialog extends FormViewDialog {
    static props = {
        ...CustomAppointmentFormViewDialog.props,
        inviteUrl: String,
        onLinkCopied: Function,
    };

    setup() {
        super.setup();
        Object.assign(this.viewProps, {
            buttonTemplate: 'appointment.FormViewDialog.buttons',
            inviteUrl: this.props.inviteUrl,
            onLinkCopied: this.props.onLinkCopied.bind(this),
            jsClass: "appointment_type_view_form_custom_share",
        });
    }
}

registry.category('views').add('appointment_type_view_form_custom_share', {
    ...formView,
    Controller: CustomAppointmentFormController,
});
