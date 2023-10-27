/* @odoo-module */

import { RATING } from "@im_livechat/embed/core/livechat_service";
import { TranscriptSender } from "@im_livechat/embed/feedback_panel/transcript_sender";

import { Component, useState } from "@odoo/owl";
import { url } from "@web/core/utils/urls";

/**
 * @typedef {Object} Props
 * @property {Function} [onClickClose]
 * @property {Function} [sendFeedback]
 * @property {import("@mail/core/common/thread_model").Thread}
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
        this.state = useState({
            step: this.STEP.RATING,
            rating: null,
            feedback: "",
        });
        this.url = url;
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
