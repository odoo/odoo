import { patch } from "@web/core/utils/patch";
import { ProductProduct } from "@point_of_sale/app/models/product_product";

patch(ProductProduct.prototype, {
    getTemplateImageUrl() {
        return (
            (this.image_128 &&
                `/web/image?model=product.template&field=image_128&id=${this.raw.product_tmpl_id}&unique=${this.write_date}`) ||
            ""
        );
    },
});
