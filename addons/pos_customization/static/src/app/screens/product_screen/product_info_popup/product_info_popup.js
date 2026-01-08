import { patch } from "@web/core/utils/patch";
import { ProductInfoPopup } from "@point_of_sale/app/screens/product_screen/product_info_popup/product_info_popup";
import { useService } from "@web/core/utils/hooks";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";

ProductInfoPopup.components = {
    ...ProductInfoPopup.components,
    ProductCard,
};
patch(ProductInfoPopup.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    },
    getProductImage(product) {
        return product.getTemplateImageUrl();
    },
    async addProductToOrder(product) {
        await this.pos.addLineToCurrentOrder({ product_id: product });
    },
    async onProductInfoClick(product) {
        const info = await this.pos.getProductInfo(product, 1);
        this.dialog.add(ProductInfoPopup, { info: info, product: product });
    },
});
