import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { PaymentProviderFormController } from "./payment_provider_form_controller";

export const paymentProviderFormView = {
    ...formView,
    Controller: PaymentProviderFormController,
};

registry.category("views").add("payment_provider_form", paymentProviderFormView);
