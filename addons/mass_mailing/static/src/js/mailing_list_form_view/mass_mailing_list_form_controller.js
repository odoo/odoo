import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { MailingListPickerDialog } from "../../components/mailing_list_picker_dialog/mailing_list_picker_dialog";

export class MailingListFormController extends FormController {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }
    /**
     * @override
     */
    async create() {
        this.dialog.add(MailingListPickerDialog, {});
    }
}
