import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class ProductVariantPreviewImageHover extends Interaction {
    static selector = '.oe_product_cart.o_has_variations';
    dynamicContent = {
        '.o_product_variant_preview': {
            't-on-mouseenter': this._mouseEnter,
            't-on-mouseleave': this._mouseLeave,
            't-on-click': this._onClick,
        },
    };

    setup() {
        this.productImg = this.el.querySelector('.oe_product_image_img_wrapper_primary img');
        this.originalImgSrc = this.productImg.getAttribute('src');
    }

    /**
     * Display the variant image on hover.
     *
     * @private
     * @param {Event} ev
     *
     * @returns {void}
     */
    _mouseEnter(ev) {
        if (!this.env.isSmall) {
            const variantImageSrc = ev.target.dataset.variantImage;
            if (!variantImageSrc) {
                return;
            }
            this._setImgSrc(variantImageSrc);
        }
    }

    /**
     * Reset the product image when mouse no longer hovers on the ptav.
     *
     * @private
     *
     * @returns {void}
     */
    _mouseLeave() {
        if (!this.env.isSmall) {
            this._setImgSrc(this.originalImgSrc);
        }
    }

    /**
     * Set the image source of the product to the given image source
     *
     * @param {string} imageSrc
     */
    _setImgSrc(imageSrc) {
        this.productImg.src = imageSrc;
    }

    /**
     * On mobile, when ptav is clicked simulate on hover behavior and change product image
     * to variant image.
     * The href of product card is changed to match that of the selected variant.
     *
     * @param {Event} ev
     * @returns
     */
    _onClick(ev) {
        if (this.env.isSmall) {
            ev.preventDefault();
            const targetElement = ev.target.closest('.o_product_variant_preview');
            const productCard = ev.target.closest('.oe_product_cart');
            productCard.querySelector('.oe_product_image_link').href = targetElement.href;
            const variantImageSrc = targetElement.dataset.variantImage;
            if (!variantImageSrc) {
                return;
            }
            this._setImgSrc(variantImageSrc);
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale.product_variant_preview_image_hover', ProductVariantPreviewImageHover);
