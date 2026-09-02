import { Component, markup, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";

const { DateTime } = luxon;

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

    formatTicketPrice(ticket) {
        const order = this.pos.getOrder();
        return this.pos.formatCurrency(ticket.price, order?.currency?.id);
    }

    formatEventDate(dateValue) {
        if (!dateValue) {
            return "";
        }
        const dt =
            dateValue instanceof DateTime ? dateValue : DateTime.fromJSDate(new Date(dateValue));
        return dt.toFormat("MMM dd yyyy, h:mm a");
    }
}
