import publicWidget from "@web/legacy/js/public/public_widget";
import { session } from "@web/session";
import { renderToElement } from "@web/core/utils/render";
import { rpc } from "@web/core/network/rpc";

/**
 * Global widget for both fullscreen view and non-fullscreen view of a slide course.
 * Contains general methods to update the UI elements (progress bar, sidebar...) as well
 * as method to mark the slide as completed / uncompleted.
 */
export const SlideCoursePage = publicWidget.Widget.extend({
    events: {
        "click button.o_wslides_button_complete": "onCompleteClick",
    },

    custom_events: {
        slide_completed: "onSlideCompleted",
        slide_mark_completed: "onSlideMarkCompleted",
    },

    /**
     * Collapse the next category when the current one has just been completed
     */
    collapseNextCategory(nextCategoryId) {
        const categorySection = document.getElementById(`category-collapse-${nextCategoryId}`);
        if (categorySection?.getAttribute("aria-expanded") === "false") {
            categorySection.setAttribute("aria-expanded", true);
            document.querySelector(`ul[id=collapse-${nextCategoryId}]`).classList.add("show");
        }
    },

    /**
     * Greens up the bullet when the slide is completed
     * @param {Object} slide
     * @param {Boolean} completed
     */
    toggleCompletionButton(slide, completed = true) {
        const $button = this.$(`.o_wslides_sidebar_done_button[data-id="${slide.id}"]`);

        if (!$button.length) {
            return;
        }

        const newButton = renderToElement("website.slides.sidebar.done.button", {
            slideId: slide.id,
            uncompletedIcon: $button.data("uncompletedIcon") ?? "fa-circle-thin",
            slideCompleted: completed ? 1 : 0,
            canSelfMarkUncompleted: slide.canSelfMarkUncompleted,
            canSelfMarkCompleted: slide.canSelfMarkCompleted,
            isMember: slide.isMember,
        });
        $button.replaceWith(newButton);
    },

    /**
     * Updates the progressbar whenever a lesson is completed
     * @param {Integer} channelCompletion
     */
    updateProgressbar(channelCompletion) {
        const completion = Math.min(100, channelCompletion);

        const $completed = $(".o_wslides_channel_completion_completed");
        const $progressbar = $(".o_wslides_channel_completion_progressbar");

        if (completion < 100) {
            // Hide the "Completed" text and show the progress bar
            $completed.addClass("d-none");
            $progressbar.removeClass("d-none").addClass("d-flex");
        } else {
            // Hide the progress bar and show the "Completed" text
            $completed.removeClass("d-none");
            $progressbar.addClass("d-none").removeClass("d-flex");
        }

        $progressbar.find(".progress-bar").css("width", `${completion}%`);
        $progressbar.find(".o_wslides_progress_percentage").text(completion);
    },

    /**
     * Once the completion conditions are filled,
     * rpc call to set the relation between the slide and the user as "completed"
     *
     * @param {Object} slide: slide to set as completed
     * @param {Boolean} completed: true to mark the slide as completed
     *     false to mark the slide as not completed
     */
    async toggleSlideCompleted(slide, completed = true) {
        if (!!slide.completed === !!completed || !slide.isMember || !slide.canSelfMarkCompleted) {
            // no useless RPC call
            return;
        }

        const data = await rpc(`/slides/slide/${completed ? "set_completed" : "set_uncompleted"}`, {
            slide_id: slide.id,
        });

        this.toggleCompletionButton(slide, completed);
        this.updateProgressbar(data.channel_completion);
        if (data.next_category_id) {
            this.collapseNextCategory(data.next_category_id);
        }
    },
    /**
     * Retrieve the slide data corresponding to the slide id given in argument.
     * This method used the "slide_sidebar_done_button" template.
     * @param {Integer} slideId
     */
    _getSlide: function (slideId) {
        return $(`.o_wslides_sidebar_done_button[data-id="${slideId}"]`).data();
    },

    /**
     * We clicked on the "done" button.
     * It will make a RPC call to update the slide state and update the UI.
     */
    onCompleteClick(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const $button = $(ev.currentTarget).closest(".o_wslides_sidebar_done_button");

        const slideData = $button.data();
        const isCompleted = Boolean(slideData.completed);

        this.toggleSlideCompleted(slideData, !isCompleted);
    },

    /**
     * The slide has been completed, update the UI
     */
    onSlideCompleted(ev) {
        const slideId = ev.data.slideId;
        const completed = ev.data.completed;
        const slide = this._getSlide(slideId);
        if (slide) {
            // Just joined the course (e.g. When "Submit & Join" action), update the UI
            this.toggleCompletionButton(slide, completed);
        }
        this.updateProgressbar(ev.data.channelCompletion);
    },

    /**
     * Make a RPC call to complete the slide then update the UI
     */
    onSlideMarkCompleted(ev) {
        if (!session.is_website_user) {
            // no useless RPC call
            const slide = this._getSlide(ev.data.id);
            this.toggleSlideCompleted(slide, true);
        }
    },
});
