import { _t } from '@web/core/l10n/translation';
import { ConfirmationDialog, deleteConfirmationMessage } from '@web/core/confirmation_dialog/confirmation_dialog';
import { ListRenderer } from '@web/views/list/list_renderer';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { X2ManyField, x2ManyField } from '@web/views/fields/x2many/x2many_field';

export const questionAnswerDeleteConfirmationMessage = _t(
    `Are you sure you want to delete this answer? There are already registrations with this answer, \
    all these registration answers with this answer will be lost if you confirm.

Are you sure you want to proceed?`
);

export class QuestionAnswerListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    }

    async onRemoveCellClicked(record, ev) {
        const registrations = await this.orm.call(
            "event.registration.answer",
            "search",
            [[["value_answer_id", "=", record.resId]]]
        );
        if (registrations.length > 0) {
             this.dialog.add(ConfirmationDialog, {
                title: _t("Registration answers will be deleted!"),
                body: questionAnswerDeleteConfirmationMessage,
                confirmLabel: _t("Delete"),
                confirm: () => super.onDeleteRecord(record),
                cancel: () => { },
                cancelLabel: _t("No, keep it"),
            });
        }
        else {
            super.onRemoveCellClicked(record, ev);
        }
    }

}

export class QuestionAnswerOne2ManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: QuestionAnswerListRenderer,
    };
}

export const questionAnswerOne2ManyField = {
    ...x2ManyField,
    component: QuestionAnswerOne2ManyField,
}

registry.category("fields").add("question_answer_one2many", questionAnswerOne2ManyField);
