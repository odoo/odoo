import { WebsiteSlidesProgressBar } from "@website_slides/interactions/slides_course_progressbar";

export class WebsiteSlidesCommon extends WebsiteSlidesProgressBar {
    setup() {
        super.setup();
        this.quiz = this.slidesService.data.quiz;
        this.slidesService.registerCollapseNextCategoryCallback((id) => {
            this.collapseNextCategory(id);
        });
    }

    /**
     * Collapse the next category when the current one has just been completed
     */
    collapseNextCategory(nextCategoryId) {
        const categorySectionEl = document.querySelector(`#category-collapse-${nextCategoryId}`);
        if (categorySectionEl?.getAttribute("aria-expanded") === "false") {
            categorySectionEl.setAttribute("aria-expanded", true);
            document.querySelector(`ul[id=collapse-${nextCategoryId}]`).classList.add("show");
        }
    }
}
