import { patch } from "@web/core/utils/patch";
import { WebsiteSlidesFullscreen } from "@website_slides/interactions/slides_course_fullscreen";

patch(WebsiteSlidesFullscreen.prototype, {
    extractChannelData() {
        const data = this.el.dataset;
        return { productId: Number(data.productId), ...super.extractChannelData() };
    },
});
