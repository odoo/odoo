import { ProductInfoBanner } from "@point_of_sale/app/components/product_info_banner/product_info_banner";
import { patch } from "@web/core/utils/patch";

patch(ProductInfoBanner.prototype, {
    get bannerClass() {
        const result = super.bannerClass;
        return `${result} ${
            this.props.productTemplate.self_order_available ? "bg-success" : "bg-danger"
        }`;
    },
    async switchSelfAvailability() {
        this.props.productTemplate.update({
            self_order_available: !this.props.productTemplate.self_order_available,
        });
    },
});
