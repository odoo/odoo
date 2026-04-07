import { useService } from "@web/core/utils/hooks";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { MailingListPickerDialog } from "../../components/mailing_list_picker_dialog/mailing_list_picker_dialog";

export class MailingListKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }
    /**
     * @override
     */
    async createRecord() {
        this.dialog.add(MailingListPickerDialog, {});
    }
}
