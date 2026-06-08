import { patch } from "@web/core/utils/patch";
import { WebsiteSlidesFullscreen } from "@website_slides/interactions/slides_course_fullscreen";

patch(WebsiteSlidesFullscreen.prototype, {
    extractChannelData() {
        const data = this.el.dataset;
        return {
            productId: Number(data.productId),
            currencyName: data.currencyName,
            currencySymbol: data.currencySymbol,
            price: Number(data.price),
            hasDiscountedPrice: !!data.hasDiscountedPrice,
            ...super.extractChannelData(),
        };
    },
});
