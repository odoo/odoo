import { patch } from "@web/core/utils/patch";
import { WebsiteSlidesCoursePageFullscreen } from "@website_slides/interactions/slides_course_page";

patch(WebsiteSlidesCoursePageFullscreen.prototype, {
    async renderSlide() {
        await super.renderSlide();
        if (this.slide.category === "certification") {
            const contentEl = this.el.querySelector(".o_wslides_fs_content");
            contentEl.replaceChildren();
            this.renderAt("website.slides.fullscreen.certification", this, contentEl);
        }
    },
    /**
     * Creates slides objects from every slide-list-cells attributes
     */
    getSlides() {
        const slideList = [];
        let channelSet = false;
        for (const slideEl of this.el.querySelectorAll(
            ".o_wslides_fs_sidebar_list_item[data-can-access='True']"
        )) {
            const data = slideEl.dataset;
            slideList.push({
                id: Number(data.id),
                canAccess: !!data.canAccess,
                name: data.name,
                category: data.category,
                videoSourceType: data.videoSourceType,
                slug: data.slug,
                hasQuestion: !!data.hasQuestion,
                isQuiz: !!data.isQuiz,
                completed: !!data.completed,
                embedCode: data.embedCode,
                canSelfMarkCompleted: !!data.canSelfMarkCompleted,
                canSelfMarkUncompleted: !!data.canSelfMarkUncompleted,
                emailSharing: !!data.emailSharing,
                websiteShareUrl: data.websiteShareUrl,
                certificationId: Number(data.certificationId),
            });

            if (!channelSet) {
                this.slidesService.setChannel({
                    isMember: !!data.isMember,
                    isMemberOrInvited: !!data.isMemberOrInvited,
                    canUpload: !!data.canUpload,
                });
                channelSet = true;
            }
        }
        return slideList;
    },
});
