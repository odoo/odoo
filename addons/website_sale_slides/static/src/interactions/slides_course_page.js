import { patch } from "@web/core/utils/patch";
import { WebsiteSlidesCoursePageFullscreen } from "@website_slides/interactions/slides_course_page";

patch(WebsiteSlidesCoursePageFullscreen.prototype, {
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
