/* @odoo-module */

import { PosPopupController } from "@point_of_sale/js/Popups/PosPopupController";
import { patch } from "@web/core/utils/patch";
import { PaymentTransactionPopup } from "./PaymentTransactionPopup";

patch(PosPopupController, "pos_mercury.PosPopupController", {
    components: { ...PosPopupController.components, PaymentTransactionPopup },
});
