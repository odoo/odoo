import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { MailingListPickerDialog } from "../../components/mailing_list_picker_dialog/mailing_list_picker_dialog";

export class MailingListListController extends ListController {
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
