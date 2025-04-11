import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

export const eventQuestionDeleteConfirmationMessage = _t(
    `Are you sure you want to delete those questions? There are already attendees with answers to \
some of those questions, all these answers will be lost if you confirm.

Are you sure you want to proceed?`
);

export class EventQuestionListController extends ListController {

    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async onDeleteSelectedRecords() {
        const registrations = await this.orm.call(
            "event.registration.answer",
            "search",
            [[["question_id", "in", this.actionMenuProps.getActiveIds()]]]
        );
        if (registrations.length > 0) {
            return this.deleteRecordsWithConfirmation({
                    ...super.deleteConfirmationDialogProps,
                    body: eventQuestionDeleteConfirmationMessage,
                    title: _t("Registration answers will be deleted!")
                });
        }
        return super.onDeleteSelectedRecords();
    }
}

export const EventQuestionListView = {
    ...listView,
   Controller: EventQuestionListController,
}

registry.category("views").add("event_question_list", EventQuestionListView);
