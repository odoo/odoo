import { useAutofocus } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

export class TipCell extends Component {
    static template = "point_of_sale.TipCell";
    static props = {
        order: Object,
    };

    setup() {
        this.state = useState({ isEditing: false });
        this.orderUiState = this.props.order.uiState.TipScreen;
        useAutofocus();
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
