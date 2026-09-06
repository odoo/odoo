// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { EventInfoPopup } from "@pos_event/app/components/popup/event_info_popup/event_info_popup";
import { createDummyProductForEvents, updateSeats } from "../utils/event_util";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("UPDATE_AVAILABLE_SEATS", (data) => {
            updateSeats(this.models, data);
        });

        createDummyProductForEvents(this.models);
    },
    searchProductsFromDBDomain(searchProductWord) {
        const domain = super.searchProductsFromDBDomain(searchProductWord);
        domain.push(["service_tracking", "!=", "event"]);
        return domain;
    },
    async onProductInfoClick(productTemplate, productProduct = false) {
        const selectedLine = this.getOrder()?.getSelectedOrderline();
        const isTicketLine =
            selectedLine?.event_ticket_id &&
            selectedLine.product_id.product_tmpl_id?.id === productTemplate.id;
        const event =
            productTemplate.event_id ||
            (isTicketLine ? selectedLine.event_ticket_id.event_id : null);
        if (!event) {
            return super.onProductInfoClick(...arguments);
        }
        return this.dialog.add(EventInfoPopup, {
            productTemplate: productTemplate,
            event: event,
        });
    },
});
