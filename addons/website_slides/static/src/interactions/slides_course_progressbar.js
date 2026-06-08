import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class WebsiteSlidesProgressBar extends Interaction {
    static selector = ".o_wslides_slides_list";

    dynamicSelectors = {
        ...this.dynamicSelectors,
        _progressPercentage: () =>
            document.querySelector(
                ".o_wslides_channel_completion_progressbar .o_wslides_progress_percentage"
            ),
        _progressBar: () =>
            document.querySelector(".o_wslides_channel_completion_progressbar .progress-bar"),
    };
    dynamicContent = {
        "button.o_wslides_button_complete": {
            "t-on-click.prevent.stop": this.onCompleteClick,
        },
        ".o_wslides_channel_completion_progressbar": {
            "t-att-class": () => ({
                "d-none": this.progressbarCompletion >= 100,
                "d-flex": this.progressbarCompletion < 100,
            }),
        },
        ".o_wslides_channel_completion_completed": {
            "t-att-class": () => ({ "d-none": this.progressbarCompletion < 100 }),
        },
        _progressBar: {
            "t-att-style": () => ({ width: `${this.progressbarCompletion}%` }),
        },
        _progressPercentage: {
            "t-out": () => this.progressbarCompletion,
        },
        _root: {
            "t-on-slide_completed": (ev) => this.onSlideCompleted(),
        },
    };

    setup() {
        this.slidesService = this.services.website_slides;
        this.slide = this.slidesService.data.slide;
        this.channel = this.slidesService.data.channel;
        this.slidesService.registerAfterTogglingCompletion((slide) => {
            this.onSlideCompleted(slide);
        });
        this.progressbarCompletion = parseInt(
            document.querySelector(
                ".o_wslides_channel_completion_progressbar .o_wslides_progress_percentage"
            )?.textContent || 0
        );
    }

    /**
     * Greens up the bullet when the slide is completed
     * @param {Object} slide
     */
    toggleCompletionButton(slide) {
        const buttonEl = this.el.querySelector(
            `.o_wslides_sidebar_done_button[data-id="${slide.id}"]`
        );
        if (!buttonEl) {
            return;
        }
        this.renderAt(
            "website.slides.sidebar.done.button",
            {
                slideId: slide.id,
                uncompletedIcon: buttonEl.dataset.uncompletedIcon ?? "fa-circle-thin",
                slideCompleted: slide.completed ? 1 : undefined,
                canSelfMarkUncompleted: slide.canSelfMarkUncompleted ? "True" : "",
                canSelfMarkCompleted: slide.canSelfMarkCompleted ? "True" : "",
                isMember: this.channel.isMember ? "True" : "",
            },
            buttonEl,
            "afterend"
        );
        buttonEl.remove();
    }

    /**
     * Updates the progressbar whenever a lesson is completed
     */
    updateProgressbar() {
        this.progressbarCompletion = Math.min(100, this.channel.completion);
        this.updateContent();
    }

    /**
     * We clicked on the "done" button.
     * It will toggle the slide completion in the slides service.
     */
    onCompleteClick(ev) {
        const data = ev.currentTarget.closest(".o_wslides_sidebar_done_button").dataset;
        const slide = {
            id: Number(data.id),
            uncompletedIcon: data.uncompletedIcon,
            completed: !!data.completed,
            canSelfMarkCompleted: !!data.canSelfMarkCompleted,
            canSelfMarkUncompleted: !!data.canSelfMarkUncompleted,
        };
        this.channel.isMember = !!data.isMember;
        if (data.id === this.slide.id) {
            this.slidesService.setSlide(slide);
        }
        this.slidesService.toggleCompletion(slide, !slide.completed);
    }

    /**
     * Updates the UI after toggleCompletion call in services
     *
     * @param {Object} slide: slide to set as completed
     */
    onSlideCompleted(slide = this.slide) {
        this.toggleCompletionButton(slide);
        this.updateProgressbar();
    }
}

registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesProgressBar", WebsiteSlidesProgressBar);
