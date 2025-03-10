import { patch } from "@web/core/utils/patch";
import { ProductInfoBanner as OriginalProductInfoBanner } from "@point_of_sale/app/components/product_info_banner/product_info_banner";

patch(OriginalProductInfoBanner.prototype, {
    static: {
        template: "pos_customization.ProductInfoBanner",
    },
});
