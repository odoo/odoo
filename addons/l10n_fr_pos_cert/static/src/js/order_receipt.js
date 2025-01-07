import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

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
            line.order_id.l10n_fr_hash !== false &&
            line.price_type === "manual" &&
            !this.props.basic_receipt
        ) {
            const textValue =
                _t("Old unit price:") +
                ` ${this.formatCurrency(line.taxed_lst_unit_price)} ` +
                _t("/ Units");
            info.push({
                class: "oldPrice",
                value: textValue,
            });
        }
    },
});
