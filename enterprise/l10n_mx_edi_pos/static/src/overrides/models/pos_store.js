import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { AddInfoPopup } from "@l10n_mx_edi_pos/app/add_info_popup/add_info_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";
import { lt } from "@point_of_sale/utils";

patch(PosStore.prototype, {
    async pay() {
        if (this.company.country_id?.code === "MX") {
            const currentOrder = this.get_order();
            currentOrder.recomputeOrderData();
            const isRefund = currentOrder.lines.some((x) => x.refunded_orderline_id);
            if (
                (isRefund &&
                    currentOrder.lines.some(
                        (x) => x.price_subtotal > 0.0 && !x.refunded_orderline_id && !x.coupon_id
                    )) ||
                (!isRefund &&
                    lt(currentOrder.amount_total, 0, { decimals: this.currency.decimal_places }))
            ) {
                this.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t(
                        "The amount of the order must be positive for a sale and negative for a refund."
                    ),
                });
                return;
            }
            if (currentOrder.is_to_invoice() && !currentOrder.l10n_mx_edi_usage) {
                const addedMxFields = await this.addL10nMxEdiFields(currentOrder);
                if (!addedMxFields) {
                    currentOrder.set_to_invoice(false);
                }
            }
        }

        return super.pay(...arguments);
    },
    async addL10nMxEdiFields(order) {
        const payload = await makeAwaitable(this.dialog, AddInfoPopup, { order });
        if (payload) {
            order.l10n_mx_edi_cfdi_to_public =
                payload.l10n_mx_edi_cfdi_to_public === true ||
                payload.l10n_mx_edi_cfdi_to_public === "1";
            order.l10n_mx_edi_usage = payload.l10n_mx_edi_usage;
            return true;
        }
        return false;
    },
});
