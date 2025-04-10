import { Interaction } from "@web/public/interaction";
import { renderToElement } from "@web/core/utils/render";
import { getDataFromEl } from "@web/public/utils";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";

export class WebsiteSlidesCoursePage extends Interaction {
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
            "t-on-click.prevent": this.onCompleteClick,
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
            // TODO: check that required and correct selector
            // => yes required, selector should work but not yet checked
            "t-on-slide_completed": this.onSlideCompleted,
            "t-on-slide_mark_completed": this.onSlideMarkCompleted,
        },
    };

    setup() {
        this.progressbarCompletion = parseInt(
            document.querySelector(
                ".o_wslides_channel_completion_progressbar .o_wslides_progress_percentage"
            )?.textContent || 0
        );
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

    /**
     * Greens up the bullet when the slide is completed
     * @param {Object} slide
     * @param {Boolean} completed
     */
    toggleCompletionButton(slide, completed = true) {
        const buttonEl = this.el.querySelector(
            `.o_wslides_sidebar_done_button[data-id="${slide.id}"]`
        );

        if (!buttonEl) {
            return;
        }

        const newButtonEl = renderToElement("website.slides.sidebar.done.button", {
            slideId: slide.id,
            uncompletedIcon: getDataFromEl(buttonEl).uncompletedIcon ?? "fa-circle-thin",
            slideCompleted: completed ? 1 : 0,
            canSelfMarkUncompleted: slide.canSelfMarkUncompleted,
            canSelfMarkCompleted: slide.canSelfMarkCompleted,
            isMember: slide.isMember,
        });
        buttonEl.replaceWith(newButtonEl);
    }

    /**
     * Updates the progressbar whenever a lesson is completed
     * @param {Integer} channelCompletion
     */
    updateProgressbar(channelCompletion) {
        this.progressbarCompletion = Math.min(100, channelCompletion);
        this.updateContent();
    }

    /**
     * Once the completion conditions are filled,
     * rpc call to set the relation between the slide and the user as "completed"
     * @param {Object} slide: slide to set as completed
     * @param {Boolean} completed: true to mark the slide as completed
     *     false to mark the slide as not completed
     */
    async toggleSlideCompleted(slide, completed = true) {
        if (
            !!slide.completed === !!completed ||
            slide.isMember === undefined ||
            (completed && slide.canSelfMarkCompleted === undefined) ||
            (!completed && slide.canSelfMarkUncompleted === undefined)
        ) {
            // no useless RPC call
            return;
        }

        const data = await this.waitFor(
            rpc(`/slides/slide/${completed ? "set_completed" : "set_uncompleted"}`, {
                slide_id: slide.id,
            })
        );

        this.toggleCompletionButton(slide, completed);
        this.updateProgressbar(data.channel_completion);
        if (data.next_category_id) {
            this.collapseNextCategory(data.next_category_id);
        }
    }

    /**
     * Retrieve the slide data corresponding to the slide id given in argument.
     * This method used the "slide_sidebar_done_button" template.
     * @param {Integer} slideId
     */
    getSlide(slideId) {
        return getDataFromEl(
            this.el.querySelector(`.o_wslides_sidebar_done_button[data-id="${slideId}"]`)
        );
    }

    /**
     * We clicked on the "done" button.
     * It will make a RPC call to update the slide state and update the UI.
     * @param {Event} event
     */
    onCompleteClick(event) {
        event.stopPropagation();
        const buttonEl = event.currentTarget.closest(".o_wslides_sidebar_done_button");
        const slideData = getDataFromEl(buttonEl);
        const isCompleted = Boolean(slideData.completed);
        this.toggleSlideCompleted(slideData, !isCompleted);
    }

    /**
     * The slide has been completed, update the UI
     * @param {Event} event
     */
    onSlideCompleted(event) {
        const slideId = event.detail.slideId;
        const completed = event.detail.completed;
        const slide = this.getSlide(slideId);
        if (slide) {
            // Just joined the course (e.g. When "Submit & Join" action), update the UI
            this.toggleCompletionButton(slide, completed);
        }
        this.updateProgressbar(event.detail.channelCompletion);
    }

    /**
     * Make a RPC call to complete the slide then update the UI
     * @param {Event} event
     */
    onSlideMarkCompleted(event) {
        if (!session.is_website_user) {
            // no useless RPC call
            const slide = this.getSlide(event.detail.id);
            this.toggleSlideCompleted(slide, true);
        }
    }
}
