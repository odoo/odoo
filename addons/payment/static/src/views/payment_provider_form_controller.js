import { FormController } from "@web/views/form/form_controller";

export class PaymentProviderFormController extends FormController {
    setup() {
        super.setup();
        this.canCreate = false;
    }
}
