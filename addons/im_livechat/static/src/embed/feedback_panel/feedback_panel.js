/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { session } from "@web/session";
import { TranscriptSender } from "./transcript_sender";
import { RATING } from "../core/livechat_service";

/**
 * @typedef {Object} Props
 * @property {Function} [onClickClose]
 * @property {Function} [sendFeedback]
 * @property {import("@mail/core/thread_model").Thread}
 * @extends {Component<Props, Env>}
 */
export class FeedbackPanel extends Component {
    static template = "im_livechat.FeedbackPanel";
    static props = ["onClickClose?", "sendFeedback", "thread"];
    static components = { TranscriptSender };

    STEP = Object.freeze({
        RATING: "rating",
        THANKS: "thanks",
    });
    RATING = RATING;

    setup() {
        this.session = session;
        this.state = useState({
            step: this.STEP.RATING,
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
        this.props.sendFeedback(this.state.rating, this.state.feedback);
        this.state.step = this.STEP.THANKS;
    }
}
