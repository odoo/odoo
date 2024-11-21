import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { ListContainer } from "@point_of_sale/app/generic_components/list_container/list_container";

export class OrderTabs extends Component {
    static template = "point_of_sale.OrderTabs";
    static components = {
        ListContainer,
    };
    static props = {
        orders: Array,
        class: { type: String, optional: true },
    };
    static defaultProps = {
        class: "",
    };
    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.dialog = useService("dialog");
    }
    newFloatingOrder() {
        this.pos.selectedTable = null;
        const order = this.pos.add_new_order();
        this.pos.showScreen("ProductScreen");
        this.dialog.closeAll();
        return order;
    }
    selectFloatingOrder(order) {
        this.pos.set_order(order);
        this.pos.selectedTable = null;
        const previousOrderScreen = order.get_screen_data();

        const props = {};
        if (previousOrderScreen?.name === "PaymentScreen") {
            props.orderUuid = order.uuid;
        }

        this.pos.showScreen(previousOrderScreen?.name || "ProductScreen", props);
        this.dialog.closeAll();
    }
    get orders() {
        return this.props.orders.sort((a, b) => {
            const noteA = a.floating_order_name || "";
            const noteB = b.floating_order_name || "";
            if (noteA && noteB) {
                // Both have notes
                const timePattern = /^\d{1,2}:\d{2}/;

                const aMatch = noteA.match(timePattern);
                const bMatch = noteB.match(timePattern);

                if (aMatch && bMatch) {
                    // Both have times, compare by time
                    const aTime = aMatch[0];
                    const bTime = bMatch[0];
                    // add padding to make sure the time is always 4 characters long
                    // such that, for example, 9:45 does not come after 10:00
                    const [aHour, aMinute] = aTime.split(":");
                    const [bHour, bMinute] = bTime.split(":");
                    const formattedATime = aHour.padStart(2, "0") + aMinute.padStart(2, "0");
                    const formattedBTime = bHour.padStart(2, "0") + bMinute.padStart(2, "0");
                    return formattedATime.localeCompare(formattedBTime);
                } else if ((aMatch && !bMatch) || (bMatch && !aMatch)) {
                    // One has time, the other does not
                    return aMatch ? -1 : 1;
                }
                // Neither have times, compare by note
                return noteA.localeCompare(noteB);
            } else if (noteA || noteB) {
                // a has note, b does not
                return noteA ? -1 : 1;
            } else {
                // Neither have notes, compare by tracking number
                return a.tracking_number > b.tracking_number ? 1 : -1;
            }
        });
    }
}
