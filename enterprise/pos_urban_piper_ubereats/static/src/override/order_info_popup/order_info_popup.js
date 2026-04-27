import { orderInfoPopup } from "@pos_urban_piper/point_of_sale_overrirde/app/order_info_popup/order_info_popup";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(orderInfoPopup.prototype, {
    getOrderDetails() {
        const orderDetails = super.getOrderDetails();
        const deliveryProvider = this.props?.order?.delivery_provider_id?.technical_name;
        if (deliveryProvider === "ubereats") {
            orderDetails["riderMaskCode"] = this.extPlatform?.extras?.ubereats_rider_mask_code;
            orderDetails["accessCode"] = this.extPlatform?.extras?.contact_access_code;
        }
        return orderDetails;
    },
    setup() {
        super.setup();
        this.cardsData.forEach((card) => {
            if (card.title === "Order Info") {
                card.fields.push(
                    {
                        label: _t("Contact Access Code"),
                        value: this.getOrderDetails().accessCode || "",
                    },
                    {
                        label: _t("Rider Mask Code"),
                        value: this.getOrderDetails().riderMaskCode || "",
                    }
                );
            }
        });
    },
});
