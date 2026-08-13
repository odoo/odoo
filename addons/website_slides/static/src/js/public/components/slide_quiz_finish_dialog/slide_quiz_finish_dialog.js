/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, onMounted, useState } from "@odoo/owl";
import { SlideXPProgressBar } from "@website_slides/js/public/components/slide_quiz_finish_dialog/slide_xp_progress_bar";

export class SlideQuizFinishDialog extends Component {
    static components = { Dialog, SlideXPProgressBar };
    static props = {
        close: Function,
        hasNext: Boolean,
        onClickNext: Function,
        quiz: Object,
        userId: Number,
    };
    static template = "website_slides.SlideQuizFinishDialog";

    setup() {
        super.setup();
        this.state = useState({
            animateKarmaGain: false,
            fadeRankMotivational: false,
            hideDismissBtns: true,
            showRankMotivational: false,
        });
        this.title = this.props.quiz.rankProgress.level_up ? _t("Level up!") : _t("Amazing!");
        onMounted(() => this.animateText());
    }

    //--------------------------------
    // Handler
    //--------------------------------

    onClickNext() {
        this.props.onClickNext();
        this.props.close();
    }

    //--------------------------------
    // Business methods
    //--------------------------------

    /**
     * Handles the animation of the different text such as the karma gain
     * and the motivational message when the user levels up.
     * @public
     */
    animateText() {
        browser.setTimeout(() => {
            this.state.animateKarmaGain = true;
            this.state.hideDismissBtns = false;
        }, 800);

        if (this.props.quiz.rankProgress.level_up) {
            browser.setTimeout(() => {
                this.state.fadeRankMotivational = true;
                browser.setTimeout(() => {
                    this.state.showRankMotivational = true;
                }, 800);
            }, 800);
        }
    }
}
