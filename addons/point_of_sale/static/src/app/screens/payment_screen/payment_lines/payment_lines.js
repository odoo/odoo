import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { parseFloat } from "@web/views/fields/parsers";
import { enhancedButtons } from "@point_of_sale/app/components/numpad/numpad";

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
        isRefundOrder: Boolean,
    };

    setup() {
        this.ui = useService("ui");
        this.pos = usePos();
        this.dialog = useService("dialog");
    }

    selectedLineClass(line) {
        return { "payment-terminal": line.getPaymentStatus() };
    }
    unselectedLineClass(line) {
        return {};
    }
    async selectLine(paymentline) {
        this.props.selectLine(paymentline.uuid);
        if (this.ui.isSmall) {
            this.dialog.add(NumberPopup, {
                title: _t("New amount"),
                buttons: enhancedButtons(),
                startingValue: this.env.utils.formatCurrency(paymentline.getAmount(), false),
                getPayload: (num) => {
                    this.props.updateSelectedPaymentline(parseFloat(num));
                },
            });
        }
    }
}
