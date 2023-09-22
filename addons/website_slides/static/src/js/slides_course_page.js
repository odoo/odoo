/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { session } from "@web/session";
import { renderToElement } from "@web/core/utils/render";

/**
 * Global widget for both fullscreen view and non-fullscreen view of a slide course.
 * Contains general methods to update the UI elements (progress bar, sidebar...) as well
 * as method to mark the slide as completed / uncompleted.
 */
export const SlideCoursePage = publicWidget.Widget.extend({
    events: {
        'click button.o_wslides_button_complete': '_onClickComplete',
    },

    custom_events: {
        'slide_completed': '_onSlideCompleted',
        'slide_mark_completed': '_onSlideMarkCompleted',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    /**
     * Collapse the next category when the current one has just been completed
     */
    collapseNextCategory: function (nextCategoryId) {
        const categorySection = document.getElementById(`category-collapse-${nextCategoryId}`);
        if (categorySection?.getAttribute('aria-expanded') === 'false') {
            categorySection.setAttribute('aria-expanded', true);
            document.querySelector(`ul[id=collapse-${nextCategoryId}]`).classList.add('show');
        }
    },

    /**
     * @override
     */
    start: function () {
        // TODO: we need to clean this code and make the changes in the view in master
        const $completed = $('.o_wslides_channel_completion_completed');
        const $progressbar = $('.o_wslides_channel_completion_progressbar');
        if($progressbar.hasClass('d-none')){
            $progressbar.removeClass('d-none').addClass('d-flex').addClass('hidden-progressbar-completed-tag');
        }
        if($completed.hasClass('d-none')){
            $completed.removeClass('d-none').addClass('hidden-progressbar-completed-tag');
        }
        return this._super.apply(this, arguments)
    },

    /**
     * Greens up the bullet when the slide is completed
     *
     * @public
     * @param {Object} slide
     * @param {Boolean} completed
     */
    toggleCompletionButton: function (slide, completed = true) {
        const $button = this.$(`.o_wslides_sidebar_done_button[data-id="${slide.id}"]`);

        if (!$button.length) {
            return;
        }

        const newButton = renderToElement('website.slides.sidebar.done.button', {
            slideId: slide.id,
            uncompletedIcon: $button.data('uncompletedIcon') ?? 'fa-circle-thin',
            slideCompleted: completed,
            canSelfMarkUncompleted: slide.canSelfMarkUncompleted,
            canSelfMarkCompleted: slide.canSelfMarkCompleted,
            isMember: slide.isMember,
        });
        $button.replaceWith(newButton);
    },

    /**
     * Updates the progressbar whenever a lesson is completed
     *
     * @public
     * @param {Integer} channelCompletion
     */
    updateProgressbar: function (channelCompletion) {
        const completion = Math.min(100, channelCompletion);

        const $completed = $('.o_wslides_channel_completion_completed');
        const $progressbar = $('.o_wslides_channel_completion_progressbar');

        if (completion < 100) {
            // Hide the "Completed" text and show the progress bar
            $completed.addClass('hidden-progressbar-completed-tag');
            $progressbar.removeClass('hidden-progressbar-completed-tag');
        } else {
            // Hide the progress bar and show the "Completed" text
            $completed.removeClass('hidden-progressbar-completed-tag');
            $progressbar.addClass('hidden-progressbar-completed-tag');
        }

        $progressbar.find('.progress-bar').css('width', `${completion}%`);
        $progressbar.find('.o_wslides_progress_percentage').text(completion);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Once the completion conditions are filled,
     * rpc call to set the relation between the slide and the user as "completed"
     *
     * @private
     * @param {Object} slide: slide to set as completed
     * @param {Boolean} completed: true to mark the slide as completed
     *     false to mark the slide as not completed
     */
    _toggleSlideCompleted: async function (slide, completed = true) {
        if (!!slide.completed === !!completed || !slide.isMember || !slide.canSelfMarkCompleted) {
            // no useless RPC call
            return;
        }

        const data = await this.rpc(
            `/slides/slide/${completed ? 'set_completed' : 'set_uncompleted'}`,
            {slide_id: slide.id},
        );

        this.toggleCompletionButton(slide, completed);
        this.updateProgressbar(data.channel_completion);
        if (data.next_category_id) {
            this.collapseNextCategory(data.next_category_id);
        }
    },
    /**
     * Retrieve the slide data corresponding to the slide id given in argument.
     * This method used the "slide_sidebar_done_button" template.
     *
     * @private
     * @param {Integer} slideId
     */
    _getSlide: function (slideId) {
        return $(`.o_wslides_sidebar_done_button[data-id="${slideId}"]`).data();
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------
    /**
     * We clicked on the "done" button.
     * It will make a RPC call to update the slide state and update the UI.
     *
     * @private
     * @param {Event} ev
     */
    _onClickComplete: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();

        const $button = $(ev.currentTarget).closest('.o_wslides_sidebar_done_button');

        const slideData = $button.data();
        const isCompleted = Boolean(slideData.completed);

        this._toggleSlideCompleted(slideData, !isCompleted);
    },

    /**
     * The slide has been completed, update the UI
     *
     * @private
     * @param {Event} ev
     */
    _onSlideCompleted: function (ev) {
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
     *
     * @private
     * @param {Event} ev
     */
    _onSlideMarkCompleted: function (ev) {
        if (!session.is_website_user) { // no useless RPC call
            const slide = this._getSlide(ev.data.id);
            this._toggleSlideCompleted(slide, true);
        }
    }
});
