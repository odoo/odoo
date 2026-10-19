import { useAutofocus } from "@web/core/utils/hooks";
import { Component, proxy, useProps, t, signal } from "@odoo/owl";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class TipCell extends Component {
    static template = "point_of_sale.TipCell";
    props = useProps({
        order: t.instanceOf(PosOrder),
    });

    autofocusRef = signal.ref();

    setup() {
        this.pos = usePos();
        this.state = proxy({ isEditing: false });
        this.orderUiState = this.props.order.uiState.TipScreen;
        useAutofocus({ ref: this.autofocusRef });
    }
    get tipAmountStr() {
        return this.pos.formatCurrency(this.pos.parseValidFloat(this.orderUiState.inputTipAmount));
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
