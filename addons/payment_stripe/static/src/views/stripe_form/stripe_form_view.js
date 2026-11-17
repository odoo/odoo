import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { StripeFormController } from "./stripe_form_controller";

export const stripeFormView = {
    ...formView,
    Controller: StripeFormController,
};

registry.category("views").add("stripe_form", stripeFormView);
