import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/objects";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

const ALLOW_OVERBOOKING = "event_registration_allow_overbooking";

export class EventRegistrationFormController extends FormController {
    /**
     * Confirm before saving an attendee that takes a seat the event no longer
     * has (new attendee, or state set from the status bar).
     *
     * @override
     */
    async onWillSaveRecord(record) {
        // overbooking is only allowed for the save it was confirmed for
        record.config.context = omit(record.config.context, ALLOW_OVERBOOKING);
        const { active, overbooking_message, state } = record.data;
        if (overbooking_message && active && ["open", "done"].includes(state)) {
            if (!(await this.confirmOverbooking(overbooking_message))) {
                return false;
            }
            record.config.context = { ...record.config.context, [ALLOW_OVERBOOKING]: true };
        }
        return super.onWillSaveRecord(...arguments);
    }

    /**
     * Confirm before registering an unconfirmed attendee the event has no seat for.
     *
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        const overbookingMessage = this.model.root.data.overbooking_message;
        if (clickParams.name === "action_confirm" && overbookingMessage) {
            if (!(await this.confirmOverbooking(overbookingMessage))) {
                return false;
            }
            clickParams.buttonContext = { ...clickParams.buttonContext, [ALLOW_OVERBOOKING]: true };
        }
        return super.beforeExecuteActionButton(...arguments);
    }

    confirmOverbooking(body) {
        return new Promise((resolve) => {
            this.dialogService.add(ConfirmationDialog, {
                body,
                confirmLabel: _t("Add"),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });
    }
}

export const eventRegistrationFormView = {
    ...formView,
    Controller: EventRegistrationFormController,
};

registry.category("views").add("event_registration_form", eventRegistrationFormView);
