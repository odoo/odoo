import { QRPopup } from "@point_of_sale/app/components/popups/qr_code_popup/qr_code_popup";
import { patch } from "@web/core/utils/patch";

patch(QRPopup, {
    props: {
        ...QRPopup.props,
        paymentMethod: { type: Object, optional: true },
    },
});
