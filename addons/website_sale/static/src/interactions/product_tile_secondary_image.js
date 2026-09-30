import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class ProductTileSecondaryImage extends Interaction {
    static selector = '.oe_product_image_link_has_secondary';
    dynamicContent = {
        _root: {
            "t-att-class": () => ({ "o_product_tile_scrolled": this.isSecondImgInView }),
            "t-on-scroll": (ev) => this.onScroll(ev),
        }
    };

    setup() {
        this.isSecondImgInView = false;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    onScroll(ev) {
        this.isSecondImgInView = ev.target.scrollLeft > ev.target.scrollWidth * 0.25;
    }
}

registry
    .category("public.interactions")
    .add("website.website_sale_product_tile_secondary_image", ProductTileSecondaryImage);
