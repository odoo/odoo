/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { session } from "@web/session";
import { TranscriptSender } from "./transcript_sender";

export const RATING = Object.freeze({
    GOOD: 5,
    OK: 3,
    BAD: 1,
});

const STEP = Object.freeze({
    RATING: "rating",
    THANKS: "thanks",
});

/**
 * @typedef {Object} Props
 * @property {Function} [onClickClose]
 * @property {Function} [sendFeedback]
 * @property {import("@mail/core/thread_model").Thread}
 * @extends {Component<Props, Env>}
 */
export class FeedbackPanel extends Component {
    static template = "im_livechat.FeedbackPanel";
    static props = ["onClickClose?", "sendFeedback?", "thread"];
    static components = { TranscriptSender };

    setup() {
        this.state = useState({
            step: STEP.RATING,
            rating: null,
            feedback: "",
        });
    }

    /**
     * @param {number} rating
     */
    select(rating) {
        this.state.rating = rating;
    }

    onClickSendFeedback() {
        this.props.sendFeedback?.(this.state.rating, this.state.feedback);
        this.state.step = STEP.THANKS;
    }

    get origin() {
        return session.origin;
    }

    get RATING() {
        return RATING;
    }

    get STEP() {
        return STEP;
    }

    get textareaVisible() {
        return Boolean(this.state.rating) && this.state.step === STEP.RATING;
    }
}
