import { useAutofocus } from "@web/core/utils/hooks";
import { Component, proxy, props, t, signal } from "@odoo/owl";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

export class TipCell extends Component {
    static template = "point_of_sale.TipCell";
    props = props({
        order: t.instanceOf(PosOrder),
    });

    autofocusRef = signal(null);

    setup() {
        this.state = proxy({ isEditing: false });
        this.orderUiState = this.props.order.uiState.TipScreen;
        useAutofocus({ ref: this.autofocusRef });
    }
    get tipAmountStr() {
        return this.env.utils.formatCurrency(
            this.env.utils.parseValidFloat(this.orderUiState.inputTipAmount)
        );
    }
    onBlur() {
        this.state.isEditing = false;
    }
    onKeydown(event) {
        if (event.key === "Enter") {
            this.state.isEditing = false;
        }
    }
    editTip() {
        this.state.isEditing = true;
    }
}
