/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { Component, onMounted, useState } from "@odoo/owl";

export class SlideXPProgressBar extends Component {
    static props = {
        previousRank: Object,
        newRank: Object,
        levelUp: Boolean,
    };
    static template = "website_slides.SlideXPProgressBar";

    setup() {
        super.setup();
        this.state = useState({
            hideRankBounds: true,
            rankLowerBound: this.props.previousRank.lower_bound,
            rankProgressPercentage: this.props.previousRank.progress,
            userKarma: this.props.previousRank.karma,
            rankUpperBound: this.props.previousRank.upper_bound,
        });
        onMounted(() => {
            this.animateProgressBar();
        });
    }

    //--------------------------------
    // Business methods
    //--------------------------------

    /**
     * Handles the animation of the karma gain in the following steps:
     * 1. Animate the tooltip text to increment smoothly from the old
     *    karma value to the new karma value.
     * 2a. The user doesn't level up
     *    I.   When the user doesn't level up the progress bar simply goes
     *         from the old karma value to the new karma value.
     * 2b. The user levels up
     *    I.   The first step makes the progress bar go from the old karma
     *         value to 100%.
     *    II.  The second step makes the progress bar go from 100% to 0%.
     *    III. The third and final step makes the progress bar go from 0%
     *         to the new karma value. It also changes the lower and upper
     *         bound to match the new rank.
     * @public
     */
    animateProgressBar() {
        // tooltip: karma incrementation
        const duration = this.props.levelUp ? 1700 : 800;
        const startTime = Date.now();

        const animateKarma = () => {
            const progress = (Date.now() - startTime) / duration;
            if (progress >= 1) {
                this.state.userKarma = this.props.newRank.karma;
            } else {
                this.state.userKarma = Math.ceil(
                    this.props.previousRank.karma +
                        (this.props.newRank.karma - this.props.previousRank.karma) * progress
                );
                browser.requestAnimationFrame(animateKarma);
            }
        };

        // progress bar and tooltip animations
        this.state.hideRankBounds = false;
        browser.requestAnimationFrame(animateKarma);
        this.state.rankProgressPercentage = this.props.newRank.progress;

        if (this.props.levelUp) {
            browser.setTimeout(() => {
                this.state.rankLowerBound = this.props.newRank.lower_bound;
                this.state.rankUpperBound = this.props.newRank.upper_bound;
            }, 800);
        }
    }
}
