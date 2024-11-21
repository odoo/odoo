import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { toRaw, useEffect, useRef } from "@odoo/owl";

export class MailComposerFormController extends formView.Controller {
    setup() {
        super.setup();
        toRaw(this.env.dialogData).model = "mail.compose.message";
    }
}

export class MailComposerFormRenderer extends formView.Renderer {
    setup() {
        super.setup();
        // Autofocus the visible editor in edition mode.
        this.root = useRef("compiled_view_root");
        useEffect((isInEdition, root) => {
            if (root && root.el && isInEdition) {
                const element = root.el.querySelector(".note-editable[contenteditable]");
                if (element) {
                    element.focus();
                    document.dispatchEvent(new Event("selectionchange", {}));
                }
            }
        }, () => [
            this.props.record.isInEdition,
            this.root,
            this.props.record.resId
        ]);
    }
}

registry.category("views").add("mail_composer_form", {
    ...formView,
    Controller: MailComposerFormController,
    Renderer: MailComposerFormRenderer,
});
