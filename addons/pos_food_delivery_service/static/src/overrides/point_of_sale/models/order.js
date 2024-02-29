/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.delivery_provider_name = json.delivery_provider_name;
        this.delivery_note = json.delivery_note || "";
        this.delivery_id = json.delivery_id;
        this.delivery_display_id = json.delivery_display_id;
        this.delivery_status = json.delivery_status;
    },
});
