/** @odoo-module **/

import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { toRaw } from "@odoo/owl";

export class MailComposerFormController extends formView.Controller {
    setup() {
        super.setup();
        toRaw(this.env.dialogData).model = "mail.compose.message";
    }
}

registry.category("views").add("mail_composer_form", {
    ...formView,
    Controller: MailComposerFormController,
});
