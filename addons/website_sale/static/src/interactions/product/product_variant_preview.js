import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class ProductVariantPreview extends Interaction {
    static selector = ".o_wsale_attribute_previewer";

    willStart() {
        const availableWidth = this.el.offsetWidth

        let usedWidth = 0
        for (let child of this.el.children) {
            usedWidth += child.offsetWidth
        }
        let elementsRemoved = 0
        while (usedWidth > availableWidth - 5) { // 5 pixels were added as buffer space
            const childToRemove = this.el.lastElementChild
            usedWidth -= childToRemove.offsetWidth
            elementsRemoved++
            this.el.removeChild(childToRemove)
        }
        if (elementsRemoved > 0) {
            // Remove last element to add span in its place
            this.el.removeChild(this.el.lastElementChild)
            elementsRemoved++
            const spanElement = document.createElement('span');
            spanElement.innerHTML = `
                <a href="${this.el.dataset.productHref}" class="">
                    +${elementsRemoved}
                </a>
            `
            this.el.appendChild(spanElement)
        }

    }
}

export class ProductVariantPreviewImageHover extends Interaction {
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
        this.productImg.src = imageSrc;
    }
}

registry
    .category("public.interactions")
    .add("website_sale.product_variant_preview", ProductVariantPreview);
registry
    .category("public.interactions")
    .add("website_sale.product_variant_preview_image_hover", ProductVariantPreviewImageHover);
