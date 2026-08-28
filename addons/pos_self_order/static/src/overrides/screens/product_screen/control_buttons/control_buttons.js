import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { generateQRCodeDataUrl } from "@point_of_sale/utils";
import { DynamicQrPopup } from "@pos_self_order/overrides/components/dynamic_qr_popup/dynamic_qr_popup";
import { _t } from "@web/core/l10n/translation";

patch(ControlButtons.prototype, {
    get showDynamicQr() {
        return (
            this.pos.config.module_pos_restaurant &&
            this.pos.config.self_ordering_mode === "mobile" &&
            this.pos.config.self_ordering_service_mode === "dynamic_qr"
        );
    },
    async clickDynamicQr() {
        const order = this.currentOrder;
        if (typeof order.id !== "number") {
            try {
                await this.pos.syncAllOrders({ orders: [order], throw: true });
            } catch {
                this.notification.add(_t("Something went wrong while generating the QR code"), {
                    type: "danger",
                });
                return;
            }
        }
        const url = await this.pos.data.call("pos.config", "get_dynamic_qr_url", [
            this.pos.config.id,
            order.id,
        ]);
        if (!url) {
            this.notification.add(_t("Something went wrong while generating the QR code"), {
                type: "danger",
            });
            return;
        }
        const qrCode = generateQRCodeDataUrl(url);
        this.dialog.add(
            DynamicQrPopup,
            { qrCode, url, order },
            { onClose: () => this.pos.updateCustomerDisplayQrData(null) }
        );
        this.pos.updateCustomerDisplayQrData(qrCode, { title: _t("Scan to join the order") });
    },
});
