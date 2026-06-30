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
        this.pos.navigate("ProductScreen", {
            orderUuid: order.uuid,
        });
        return order;
    }
    selectFloatingOrder(order) {
        this.pos.setOrder(order);
        const previousOrderScreen = order.getScreenData();
        this.pos.navigate(previousOrderScreen?.name || "ProductScreen", {
            orderUuid: order.uuid,
        });
        this.dialog.closeAll();
    }
}
