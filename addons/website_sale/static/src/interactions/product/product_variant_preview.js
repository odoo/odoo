import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class ProductVariantPreview extends Interaction {
    static selector = ".oe_product_cart";
    dynamicContent = {
        '.o_product_variant_preview': {
            "t-on-mouseenter": this.mouseEnter,
            "t-on-mouseleave": this.mouseLeave,
        },
    };

    setup() {
        this.productImg = this.el.querySelector(".oe_product_image_img_wrapper img")
        this.originalImgSrc = this.productImg.getAttribute("src");
        this.variantImageSrc = null;
    }

    mouseEnter(ev) {
        this.variantImageSrc = ev.target.dataset.variantImage
        if (!this.variantImageSrc) {
            return;
        }
        this.setImgSrc(this.variantImageSrc);
    }

    mouseLeave() {
        this.setImgSrc(this.originalImgSrc);
    }

    setImgSrc(imageSrc) {
        debugger;
        this.productImg.src = imageSrc;
    }
}

registry
    .category("public.interactions")
    .add("website_sale.product_variant_preview", ProductVariantPreview);
