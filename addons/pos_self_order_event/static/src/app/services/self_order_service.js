import { SelfOrder } from "@pos_self_order/app/services/self_order_service";
import { createDummyProductForEvents, updateSeats } from "@pos_event/app/utils/event_util";
import { getEventOrderLineValues } from "../services/card_utils";
import { patch } from "@web/core/utils/patch";

patch(SelfOrder.prototype, {
    async setup(...args) {
        await super.setup(...args);
        this.data.connectWebSocket("UPDATE_AVAILABLE_SEATS", (data) => {
            updateSeats(this.models, data);
        });
    },
    initProducts() {
        const eventProducts = createDummyProductForEvents(this.models);
        for (const product of eventProducts) {
            product.self_order_visible = true;
            product.self_order_available = true;
        }
        this.models["event.event"].getAll().forEach((event) => {
            for (const ticket of event.event_ticket_ids) {
                const productTmpl = ticket.product_id?.product_tmpl_id;
                if (productTmpl) {
                    productTmpl.self_order_visible = false;
                }
            }
        });
        super.initProducts();
        for (const categoryId in this.productByCategIds) {
            this.productByCategIds[categoryId] = this.productByCategIds[categoryId].filter(
                (product) => product.self_order_visible
            );
        }
    },
    eventImageUrl(event) {
        return event.image_1024
            ? `/web/image/event.event/${event.id}/image_1024`
            : `/pos_self_order_event/static/src/img/placeholder_thumbnail.png`;
    },

    async addToCart(
        productTemplate,
        qty,
        customer_note,
        selectedValues = {},
        customValues = {},
        comboValues = {}
    ) {
        if (productTemplate.service_tracking !== "event") {
            return super.addToCart(...arguments);
        }
        const values = getEventOrderLineValues(
            this,
            productTemplate,
            qty,
            customer_note,
            selectedValues,
            customValues,
            comboValues
        );
        return this.models["pos.order.line"].create(values);
    },
});
