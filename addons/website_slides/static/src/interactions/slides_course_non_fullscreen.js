import { WebsiteSlidesCommon } from "@website_slides/interactions/slides_course_common";
import { redirect } from "@web/core/utils/urls";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class WebsiteSlidesNonFullscreen extends WebsiteSlidesCommon {
    static selector = ".o_wslides_lesson_main";
    setup() {
        super.setup();
        this.bindedOnQuizNextSlide = this.onQuizNextSlide.bind(this);
        this.slidesService.bus.addEventListener("slide_go_next", this.bindedOnQuizNextSlide);
    }

    destroy() {
        this.slidesService.bus.removeEventListener("slide_go_next", this.bindedOnQuizNextSlide);
    }

    onQuizNextSlide() {
        const url = this.el.querySelector(".o_wslides_js_lesson_quiz").dataset.nextSlideUrl;
        redirect(url);
    }

    async onSlideCompleted(slide = this.slide) {
        super.onSlideCompleted(slide);
        if (this.slide.id === slide.id && this.slide.hasQuestion && !slide.completed) {
            window.location.reload();
        }
        // The quiz has been submitted in a documentation and in non fullscreen view,
        // should update the button "Mark Done" to "Mark To Do"
        const doneButtonEl = this.el.querySelector(".o_wslides_done_button");
        if (doneButtonEl && slide.completed) {
            doneButtonEl.classList.remove(
                "o_wslides_done_button",
                "disabled",
                "btn-primary",
                "text-white"
            );
            doneButtonEl.classList.add("o_wslides_undone_button", "btn-light");
            doneButtonEl.removeAttribute("title");
            doneButtonEl.removeAttribute("aria-disabled");
            doneButtonEl.href = `/slides/slide/${encodeURIComponent(slide.id)}/set_uncompleted`;
            doneButtonEl.textContent = _t("Mark To Do");
        }
    }
}

registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesNonFullscreen", WebsiteSlidesNonFullscreen);
