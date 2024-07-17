import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { parseFloat } from "@web/views/fields/parsers";

export class PaymentScreenPaymentLines extends Component {
    static template = "point_of_sale.PaymentScreenPaymentLines";
    static props = {
        paymentLines: { type: Array, optional: true },
        deleteLine: Function,
        selectLine: Function,
        sendForceDone: Function,
        sendPaymentCancel: Function,
        sendPaymentRequest: Function,
        sendPaymentReverse: Function,
        updateSelectedPaymentline: Function,
    };

    setup() {
        this.ui = useState(useService("ui"));
        this.pos = usePos();
        this.dialog = useService("dialog");
    }

    formatLineAmount(paymentline) {
        return this.env.utils.formatCurrency(paymentline.get_amount(), false);
    }
    selectedLineClass(line) {
        return { "payment-terminal": line.get_payment_status() };
    }
    unselectedLineClass(line) {
        return {};
    }
    async selectLine(paymentline) {
        this.props.selectLine(paymentline.uuid);
        if (this.ui.isSmall) {
            const hiddenInput = document.querySelector(".hidden-numpad-input");
            const amountElement = document.querySelector(".payment-amount");
            if (hiddenInput) {
                hiddenInput.value = paymentline.get_amount();
                hiddenInput.style.display = "block";
                amountElement.style.visibility = "hidden";
                hiddenInput.focus();
                hiddenInput.addEventListener("blur", () => {
                    hiddenInput.style.display = "none";
                    amountElement.style.visibility = "visible";
                });
                hiddenInput.addEventListener("change", (event) => {
                    const newValue = parseFloat(event.target.value);
                    if (!isNaN(newValue)) {
                        this.props.updateSelectedPaymentline(newValue);
                    }
                });
            }
        }
    }
}
