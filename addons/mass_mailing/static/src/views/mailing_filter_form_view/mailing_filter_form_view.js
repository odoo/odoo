import { MailingFilterFormController } from "./mailing_filter_form_controller";
import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";

export const mailingFilterFormView = {
    ...formView,
    Controller: MailingFilterFormController,
};

registry.category("views").add("mailing_filter_form_view", mailingFilterFormView);
