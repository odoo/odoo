/* @odoo-module */

import { RATING } from "@im_livechat/embed/core/livechat_service";
import { TranscriptSender } from "@im_livechat/embed/feedback_panel/transcript_sender";

import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

/**
 * @typedef {Object} Props
 * @property {Function} [onClickClose]
 * @property {import("models").Thread}
 * @extends {Component<Props, Env>}
 */
export class FeedbackPanel extends Component {
    static template = "im_livechat.FeedbackPanel";
    static props = ["onClickClose?", "thread"];
    static components = { TranscriptSender };

    STEP = Object.freeze({
        RATING: "rating",
        THANKS: "thanks",
    });
    RATING = RATING;

    setup() {
        this.session = session;
        this.livechatService = useService("im_livechat.livechat");
        this.rpc = useService("rpc");
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

    async onClickSendFeedback() {
        this.rpc("/im_livechat/feedback", {
            reason: this.state.feedback,
            rate: this.state.rating,
            uuid: this.props.thread.uuid,
        });
        this.state.step = this.STEP.THANKS;
    }
}
