import { patch } from "@web/core/utils/patch";
import { WebsiteSlidesFullscreen } from "@website_slides/interactions/slides_course_fullscreen";

patch(WebsiteSlidesFullscreen.prototype, {
    /**
     * Extend the renderSlide method so that slides of category "certification"
     * are also taken into account and rendered correctly
     *
     * @override
     */
    renderSlide() {
        const didRender = super.renderSlide();
        if (didRender && this.slide.category === "certification") {
            const contentEl = this.el.querySelector(".o_wslides_fs_content");
            this.renderAt("website.slides.fullscreen.certification", this, contentEl);
        }
        return didRender;
    },

    getAdditionalSlidesData(data) {
        return { certificationId: Number(data.certificationId) };
    }
});
