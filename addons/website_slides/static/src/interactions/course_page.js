import { Interaction } from "@web/public/interaction";

import { rpc } from "@web/core/network/rpc";
import { renderToElement } from "@web/core/utils/render";
import { session } from "@web/session";

export class CoursePage extends Interaction {
    dynamicContent = {
        "button.o_wslides_button_complete": {
            "t-on-click.stop.prevent": this.onClickComplete,
        },
        _root: {
            "t-on-slide_completed": this.onSlideCompleted,
            "t-on-slide_mark_completed": this.onSlideMarkCompleted,
        },
    };

    /**
     * @param {Integer} nextCategoryId
     */
    collapseNextCategory(nextCategoryId) {
        const categorySectionEl = document.getElementById(`category-collapse-${nextCategoryId}`);
        if (categorySectionEl.getAttribute('aria-expanded') === 'false') {
            categorySectionEl.setAttribute('aria-expanded', true);
            document.querySelector(`ul[id=collapse-${nextCategoryId}]`).classList.add('show');
        }
    }

    /**
     * @param {Integer} channelCompletion
     */
    updateProgressbar(channelCompletion) {
        const completion = Math.min(100, channelCompletion);
        const isCompleted = completion == 100;

        const completedEl = document.querySelector('.o_wslides_channel_completion_completed');
        const progressbarEl = document.querySelector('.o_wslides_channel_completion_progressbar');

        completedEl.classList.toggle('d-none', !isCompleted);
        progressbarEl.classList.toggle('d-flex', !isCompleted);
        progressbarEl.classList.toggle('d-none', isCompleted);

        progressbarEl.querySelector('.progress-bar').style.width = `${completion}%`;
        progressbarEl.querySelector('.o_wslides_progress_percentage').textContent = completion;
    }


    /**
     * @param {Object} slideData
     * @param {Boolean} completed
     */
    toggleCompletionButton(slideData, completed = true) {
        const buttonEl = this.el.querySelector(`.o_wslides_sidebar_done_button[data-id="${slideData.id}"]`);

        if (!!buttonEl) {
            return;
        }

        const newButton = renderToElement('website.slides.sidebar.done.button', {
            slideId: slideData.id,
            uncompletedIcon: buttonEl.getAttribute('uncompletedIcon') ?? 'fa-circle-thin',
            slideCompleted: completed ? 1 : 0,
            canSelfMarkUncompleted: slideData.canSelfMarkUncompleted,
            canSelfMarkCompleted: slideData.canSelfMarkCompleted,
            isMember: slideData.isMember,
        });

        buttonEl.outerHTML = newButton;
    }

    /**
     * @param {Object} slideData
     * @param {Boolean} completed
     */
    async toggleSlideCompleted(slideData, completed = true) {
        if (
            !!slideData.completed === !!completed
            || !slideData.isMember
            || !slideData.canSelfMarkCompleted
        ) {
            return;
        }
        const data = await this.waitFor(rpc(
            `/slides/slide/${completed ? 'set_completed' : 'set_uncompleted'}`,
            { slide_id: slideData.id },
        ));
        this.toggleCompletionButton(slideData, completed);
        this.updateProgressbar(data.channel_completion);
        if (data.next_category_id) {
            this.collapseNextCategory(data.next_category_id);
        }
    }

    /**
     * @param {Integer} slideId
     */
    getSlide(slideId) {
        return document.querySelector(`.o_wslides_sidebar_done_button[data-id="${slideId}"]`).dataset;
    }

    /**
     * @param {MouseEvent} ev
     */
    onClickComplete(ev) {
        const slideData = ev.currentTarget.closest('.o_wslides_sidebar_done_button').dataset;
        const isCompleted = Boolean(slideData.completed);
        this.toggleSlideCompleted(slideData, !isCompleted);
    }

    /**
     * @param {Event} ev
     */
    onSlideCompleted(ev) {
        const slideId = ev.data.slideId;
        const completed = ev.data.completed;
        const slideData = this.getSlide(slideId);
        if (slideData) {
            // Just joined the course (e.g. When "Submit & Join" action), update the UI
            this.toggleCompletionButton(slideData, completed);
        }
        this.updateProgressbar(ev.data.channelCompletion);
    }

    /**
     * @param {Event} ev
     */
    onSlideMarkCompleted(ev) {
        if (!session.is_website_user) {
            const slideData = this.getSlide(ev.data.id);
            this.toggleSlideCompleted(slideData, true);
        }
    }
}
