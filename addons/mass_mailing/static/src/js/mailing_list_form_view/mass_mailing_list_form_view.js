import { formView } from "@web/views/form/form_view";
import { MailingListFormController } from "./mass_mailing_list_form_controller";
import { registry } from "@web/core/registry";

export const MailingListFormView = {
    ...formView,
    Controller: MailingListFormController,
};
registry.category("views").add("mailing_list_form_view", MailingListFormView);
