import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

export class AvatarUserFormViewDialog extends FormViewDialog {
    setup() {
        super.setup();
        Object.assign(this.viewProps, {
            buttonTemplate: this.props.isToMany
                ? "mail.UserFormViewDialog.ToMany.buttons"
                : "mail.UserFormViewDialog.ToOne.buttons",
        });
    }
}
