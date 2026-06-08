import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

export class AllocationFormViewDialog extends FormViewDialog {
    setup() {
        super.setup();
        Object.assign(this.viewProps, {
            buttonDialogTemplate: "hr_holidays.AllocationFormViewDialog.buttons",
        });
    }
};
