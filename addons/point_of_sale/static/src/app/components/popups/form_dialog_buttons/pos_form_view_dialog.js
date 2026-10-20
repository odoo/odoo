import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

export class PosFormViewDialog extends FormViewDialog {
    setup() {
        super.setup();
        this.viewProps.buttonTemplate = "point_of_sale.FormDialogButtons";
    }
}
