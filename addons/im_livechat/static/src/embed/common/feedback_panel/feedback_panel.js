import { RATING } from "@im_livechat/embed/common/livechat_service";
import { TranscriptSender } from "@im_livechat/embed/common/feedback_panel/transcript_sender";

import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { url } from "@web/core/utils/urls";
import { rpc } from "@web/core/network/rpc";

/**
 * @typedef {Object} Props
 * @property {Function} [onClickClose]
 * @property {import("models").Thread}
 * @extends {Component<Props, Env>}
 */
export class FeedbackPanel extends Component {
    static template = "im_livechat.FeedbackPanel";
    static props = ["onClickClose?", "onClickNewSession", "thread"];
    static components = { TranscriptSender };

    STEP = Object.freeze({
        RATING: "rating",
        THANKS: "thanks",
    });
    RATING = RATING;

    setup() {
        this.session = session;
        this.livechatService = useService("im_livechat.livechat");
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
        rpc("/im_livechat/feedback", {
            reason: this.state.feedback,
            rate: this.state.rating,
            channel_id: this.props.thread.id,
        });
        this.state.step = this.STEP.THANKS;
    }
}
