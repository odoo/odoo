import { patch } from "@web/core/utils/patch";
import { ProductInfoPopup as OriginalProductInfoPopup } from "@point_of_sale/app/screens/product_screen/product_info_popup/product_info_popup";

patch(OriginalProductInfoPopup.prototype, {
    static: {
        template: "pos_customization.ProductInfoPopup",
    },
});
