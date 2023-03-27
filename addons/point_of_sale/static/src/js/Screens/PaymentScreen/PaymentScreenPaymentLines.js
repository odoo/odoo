/** @odoo-module */

import { NumberPopup } from "@point_of_sale/js/Popups/NumberPopup";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";

export class PaymentScreenPaymentLines extends Component {
    static template = "PaymentScreenPaymentLines";

    setup() {
        super.setup();
        this.ui = useState(useService("ui"));
        this.popup = useService("popup");
        this.pos = usePos();
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
            const { confirmed, payload } = await this.popup.add(NumberPopup, {
                title: this.env._t("New amount"),
                startingValue: parseFloat(paymentline.amount),
                isInputSelected: true,
                nbrDecimal: this.pos.globalState.currency.decimal_places,
            });

            if (confirmed) {
                this.props.updateSelectedPaymentline(parseFloat(payload));
            }
        }
        return;
    }
}
