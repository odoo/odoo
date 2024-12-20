import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class Product extends Interaction {
    static selector = "#product_detail_main";
    dynamicContent = {
        "#add_to_cart": {
            "t-on-click": this.addToCart,
        },
    };

    addToCart(ev) {
        this.services.websiteSale.addToCart({
            productTemplateId: 9,
        });
    }
}

registry.category("public.interactions").add("website_sale.product", Product);
