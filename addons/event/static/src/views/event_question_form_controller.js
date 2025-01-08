import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

export const eventQuestionDeleteConfirmationMessage = _t(
    `Are you sure you want to delete this question? There are already attendees with answers to \
this question, all these answers will be lost if you confirm.

Are you sure you want to proceed?`
);

export class EventQuestionFormController extends FormController {

    async deleteRecord() {
        const registrations = await this.orm.call(
            "event.registration.answer",
            "search",
            [[["question_id", "=", this.model.root.resId]]]
        );
        if (registrations.length > 0) {
            return this.deleteRecordsWithConfirmation({
                    ...super.deleteConfirmationDialogProps,
                    body: eventQuestionDeleteConfirmationMessage,
                    title: _t("Registration answers will be deleted!")
                });
        }
        return super.deleteRecord();
    }
}

export const eventQuestionFormView = {
    ...formView,
    Controller: EventQuestionFormController,
};

registry.category("views").add("event_question_form", eventQuestionFormView);