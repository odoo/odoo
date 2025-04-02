import { patch } from "@web/core/utils/patch";
import { WebsiteSlidesCoursePageFullscreen } from "@website_slides/interactions/slides_course_page";

patch(WebsiteSlidesCoursePageFullscreen.prototype, {
    /**
     * Extend the renderSlide method so that slides of category "certification"
     * are also taken into account and rendered correctly
     *
     * @override
     */
    renderSlide() {
        const didRender = super.renderSlide();
        if (didRender) {
            const contentEl = this.el.querySelector(".o_wslides_fs_content");
            if (this.slide.category === "certification") {
                this.renderAt("website.slides.fullscreen.certification", this, contentEl);
            }
        }
        return didRender;
    },
});
