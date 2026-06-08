import { patch } from "@web/core/utils/patch";
import { WebsiteSlidesQuizEdit } from "@website_slides/interactions/slides_course_quiz_edit";

// TODO: I think it's totally useless, check if we need it in normal view interaction
patch(WebsiteSlidesQuizEdit.prototype, {
    initServiceData() {
        super.initServiceData();
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
