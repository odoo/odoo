import { patch } from "@web/core/utils/patch";
import { WebsiteSlidesQuizEdit } from "@website_slides/interactions/slides_course_quiz_edit";

patch(WebsiteSlidesQuizEdit.prototype, {
    initServiceData() {
        super.initServiceData();
        const data = this.el.dataset;
        if (data.channelId) {
            this.slidesService.setChannel({ productId: Number(data.productId) });
        }
    },
});
