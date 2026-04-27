import { patch } from "@web/core/utils/patch";
import { Order } from "@pos_preparation_display/app/components/order/order";

patch(Order.prototype, {
    get cardColor() {
        const cardColor = super.cardColor;
        const tableStandNumber = this.props.order.table_stand_number;
        return tableStandNumber ? "o_pdis_card_color_" + (tableStandNumber % 9) : cardColor;
    },
});
