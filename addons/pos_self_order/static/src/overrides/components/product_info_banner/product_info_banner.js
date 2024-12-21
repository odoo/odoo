import { ProductInfoBanner } from "@point_of_sale/app/components/product_info_banner/product_info_banner";
import { patch } from "@web/core/utils/patch";

patch(ProductInfoBanner.prototype, {
    get bannerClass() {
        const result = super.bannerClass;
        return `${result} ${
            this.props.productTemplate.self_order_available ? "bg-success" : "bg-danger"
        }`;
    },
<<<<<<< master
    async switchSelfAvailability() {
        await this.pos.data.write("product.template", [this.props.productTemplate.id], {
            self_order_available: !this.props.productTemplate.self_order_available,
        });
    },
||||||| be92a1a25fd20a4dd636a1f1ce2b2f6c34077f5d
    async switchSelfAvailability() {
        await this.pos.data.write("product.product", [this.props.product.id], {
            self_order_available: !this.props.product.self_order_available,
        });
    },
=======
>>>>>>> a2359057961f4d06339e3481fdb3ecfd2991e2a8
});
