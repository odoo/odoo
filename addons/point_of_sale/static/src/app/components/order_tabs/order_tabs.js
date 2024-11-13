import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { ListContainer } from "@point_of_sale/app/components/list_container/list_container";

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
    async newFloatingOrder() {
        const order = this.pos.add_new_order();
        this.pos.showNumpadScreen("ProductScreen");
        this.dialog.closeAll();
        return order;
    }
    selectFloatingOrder(order) {
        this.pos.set_order(order);
        const previousOrderScreen = order.get_screen_data();

        if (previousOrderScreen?.name === "PaymentScreen") {
            this.pos.showScreen("PaymentScreen", {
                orderUuid: order.uuid,
            });
        }

        this.pos.showNumpadScreen("ProductScreen");
        this.dialog.closeAll();
    }
}
