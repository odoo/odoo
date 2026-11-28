import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    getStatus(order) {
        if (order.source !== "kiosk" && order.source !== "mobile") {
            return super.getStatus(order);
        }

        if (order.state === "cancel") {
            return _t("Cancelled");
        } else if (order.finalized) {
            if (order.raw.account_move) {
                return _t("Invoiced");
            }

            return _t("Paid");
        } else {
            return _t("Ongoing");
        }
    },
    async onClickScanOrder(qrcode) {
        const accessToken =
            URL.canParse(qrcode) && new URL(qrcode).searchParams.get("order_identifier");
        if (!accessToken) {
            return super.onClickScanOrder(...arguments);
        }
        const [order] = await this.pos.data.loadServerOrders([
            ["access_token", "=", accessToken],
            ["config_id", "=", this.pos.config.id],
        ]);
        if (!order) {
            this.env.services.notification.add(_t("Invalid QR Code! Please, Scan again!"), {
                type: "warning",
            });
            return;
        }
        this.state.filter = order.finalized ? "SYNCED" : "ACTIVE_ORDERS";
        this.setSelectedOrder(order);
        this.pos.scanning = false;
    },
    getTableTag(order) {
        return super.getTableTag(order) || order?.self_ordering_table_id?.table_number;
    },
    _getSearchFields() {
        return Object.assign({}, super._getSearchFields(...arguments), {
            SOURCE: {
                repr: (order) => order.source,
                displayName: _t("Source"),
                modelFields: ["source"],
            },
        });
    },
});
