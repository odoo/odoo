import { Component, markup, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";
import { toggleEventFavorite } from "../../../utils/event_util";

export class EventInfoPopup extends Component {
    static template = "pos_event.EventInfoPopup";
    static components = { Dialog };

    props = useProps({
        productTemplate: t.instanceOf(ProductTemplate),
        event: t.object(),
        close: t.function(),
    });

    setup() {
        this.pos = usePos();
    }

    get eventDescriptionMarkup() {
        return this.props.event.description ? markup(this.props.event.description) : "";
    }

    toggleFavorite() {
        const isFavorite = toggleEventFavorite(this.props.event.id);
        this.pos.data.write("product.template", [this.props.productTemplate.id], {
            is_favorite: isFavorite,
        });
    }

    formatTicketPrice(ticket) {
        const order = this.pos.getOrder();
        return this.pos.formatCurrency(ticket.price, order?.currency?.id);
    }
}
