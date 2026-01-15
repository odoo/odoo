import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class MassMailingContenteditablePlugin extends Plugin {
    static id = "massMailingContenteditablePlugin";
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    setup() {
        const layoutEditable = this.editable.querySelector(".o_layout .o_mail_no_options");
        if (layoutEditable) {
            this.editable.setAttribute("contenteditable", "false");
            layoutEditable.setAttribute("contenteditable", "true");
        }
    }

    cleanForSave({ root: clone }) {
        clone.querySelector(".o_layout .o_mail_no_options")?.removeAttribute("contenteditable");
    }
}

registry
    .category("basic-editor-plugins")
    .add(MassMailingContenteditablePlugin.id, MassMailingContenteditablePlugin);
