import { EmailTemplateFormController } from "@mail/views/web/form/email_template_form_controller";
import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";

export const EmailTemplateFormView = {
    ...formView,
    Controller: EmailTemplateFormController,
};

registry.category("views").add("email_template_form_view", EmailTemplateFormView);
