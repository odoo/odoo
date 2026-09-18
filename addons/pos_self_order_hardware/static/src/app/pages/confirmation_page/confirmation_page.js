import { patch } from "@web/core/utils/patch";
import { ConfirmationPage } from "@pos_self_order/app/pages/confirmation_page/confirmation_page";

patch(ConfirmationPage.prototype, {
    setup() {
        super.setup(...arguments);
        this.selfOrder.ledController.setSuccess();
    },
});
