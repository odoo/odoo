import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { onMounted } from "@odoo/owl";

export class AvatarUserFormViewDialog extends FormViewDialog {
    setup() {
        super.setup();
        Object.assign(this.viewProps, {
            buttonTemplate: this.props.isToMany
                ? "mail.UserFormViewDialog.ToMany.buttons"
                : "mail.UserFormViewDialog.ToOne.buttons",
        });

        onMounted(() => {
            setTimeout(() => {
                const input = this.modalRef.el.querySelector("#name_0");
                if (input) {
                    input.focus();
                }
            });
        });
    }
}
