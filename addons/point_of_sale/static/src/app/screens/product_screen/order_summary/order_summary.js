import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/components/order_widget/order_widget";
import { useService } from "@web/core/utils/hooks";

export class OrderSummary extends Component {
    static template = "point_of_sale.OrderSummary";
    static components = {
        Orderline,
        OrderWidget,
    };
    static props = {
        numberBufferReset: Function,
    };

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.pos = usePos();
    }

    get currentOrder() {
        return this.pos.getOrder();
    }

    async editPackLotLines(line) {
        const isAllowOnlyOneLot = line.product_id.isAllowOnlyOneLot();
        const editedPackLotLines = await this.pos.editLots(
            line.product_id,
            line.getPackLotLinesToEdit(isAllowOnlyOneLot)
        );

        line.editPackLotLines(editedPackLotLines);
    }

    clickLine(ev, orderline) {
        if (ev.detail === 2) {
            clearTimeout(this.singleClick);
            return;
        }
        this.props.numberBufferReset();
        if (!orderline.isSelected()) {
            this.pos.selectOrderLine(this.currentOrder, orderline);
        } else {
            this.singleClick = setTimeout(() => {
                this.pos.getOrder().uiState.selected_orderline_uuid = null;
            }, 300);
        }
    }
}
