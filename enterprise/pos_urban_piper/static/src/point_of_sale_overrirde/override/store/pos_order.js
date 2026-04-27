import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals);
        this.isDeliveryRefundOrder = false;
        if (!this.uiState) {
            this.uiState = {
                ...this.uiState,
                orderAcceptTime: 0,
            };
        }
    },

    get_delivery_provider_name() {
        return this.delivery_provider_id ? this.delivery_provider_id.name : "";
    },

    get_order_status() {
        return this.delivery_status ? this.delivery_status : "";
    },

    export_for_printing(baseUrl, headerData) {
        const data = super.export_for_printing(baseUrl, headerData);
        data.headerData.deliveryId = this.delivery_identifier;
        data.headerData.deliveryChannel = this.delivery_provider_id?.name;
        data.headerData.providerOrderId = this.getProviderOrderId;
        data.partner = this.partner_id;
        return data;
    },

    get deliveryOrderType() {
        const deliveryJson = JSON.parse(this?.delivery_json || "{}");
        return deliveryJson?.order?.details?.ext_platforms?.[0]?.delivery_type;
    },

    isFutureOrder() {
        return false;
    },
    get getProviderOrderId() {
        return JSON.parse(this.delivery_json || "{}").order?.details?.ext_platforms?.[0].id || "";
    },
});
