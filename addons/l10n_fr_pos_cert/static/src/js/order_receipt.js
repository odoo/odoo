import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    get qrCode() {
        if (this.order.is_french_country()) {
            return false;
        }
        return super.qrCode;
    },
    _getAdditionalLineInfo(line) {
        const info = super._getAdditionalLineInfo(line);
        if (
            line.order_id.l10n_fr_hash &&
            line.price_type === "manual" &&
            !this.props.basic_receipt
        ) {
            info.push({
                class: "oldPrice",
                value: _t(
                    "Old unit price: %s / Units",
                    this.formatCurrency(line.getTaxedlstUnitPrice())
                ),
            });
        }
        return info;
    },
});
