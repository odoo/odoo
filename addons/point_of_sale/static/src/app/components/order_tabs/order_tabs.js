import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
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
        this.ui = useService("ui");
        this.dialog = useService("dialog");
    }
    async newFloatingOrder() {
        const order = this.pos.addNewOrder();
        this.pos.showScreen("ProductScreen");
        this.dialog.closeAll();
        return order;
    }
    selectFloatingOrder(order) {
        this.pos.setOrder(order);
        const previousOrderScreen = order.getScreenData();

        const props = {};
        if (previousOrderScreen?.name === "PaymentScreen") {
            props.orderUuid = order.uuid;
        }

        this.pos.showScreen(previousOrderScreen?.name || "ProductScreen", props);
        this.dialog.closeAll();
    }
}
