import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";


export class CalendarFormDialog extends FormViewDialog {
    setup() {
        super.setup();
        Object.assign(this.viewProps, {
            ...this.viewProps,
            buttonDialogTemplate: "calendar.CalendarFormDialogButtons",
        });
    }
}
