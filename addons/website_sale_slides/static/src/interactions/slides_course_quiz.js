import { patch } from "@web/core/utils/patch";
import { WebsiteSlidesQuizNoFullscreen } from "@website_slides/interactions/slides_course_quiz";

patch(WebsiteSlidesQuizNoFullscreen.prototype, {
    setup() {
        super.setup();
        const data = this.el.dataset;
        if (data.channelId) {
            this.slidesService.setChannel({
                productId: Number(data.productId),
                currencyName: data.currencyName,
                currencySymbol: data.currencySymbol,
                price: Number(data.price),
                hasDiscountedPrice: !!data.hasDiscountedPrice,
            });
        }
    },
});
