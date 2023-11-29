/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { parseFloat } from "@web/views/fields/parsers";

export class PaymentScreenPaymentLines extends Component {
    static template = "point_of_sale.PaymentScreenPaymentLines";
    static props = {
        paymentlines: Array,
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
        this.props.selectLine(paymentline.cid);
        if (this.ui.isSmall) {
            this.dialog.add(NumberPopup, {
                title: _t("New amount"),
                startingValue: paymentline.get_amount(),
                isInputSelected: true,
                nbrDecimal: this.pos.currency.decimal_places,
                getPayload: (num) => {
                    this.props.updateSelectedPaymentline(parseFloat(num));
                },
            });
        }
    }
}
