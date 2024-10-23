import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useEffect } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
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
        useEffect(
            () => {
                const lines = this.pos.get_order().lines;
                if (lines.length && !lines.some((l) => l.isSelected())) {
                    this.pos.selectOrderLine(this.currentOrder, lines.at(-1));
                }
            },
            () => []
        );
    }

    get currentOrder() {
        return this.pos.get_order();
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
        // FIXME
        this.props.numberBufferReset();
        if (!orderline.isSelected()) {
            this.pos.selectOrderLine(this.currentOrder, orderline);
        } else {
            this.singleClick = setTimeout(() => {
                this.pos.get_order().uiState.selected_orderline_uuid = null;
            }, 300);
        }
    }
}
