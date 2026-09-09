import { TranscriptSender } from "@im_livechat/core/common/transcript_sender";

import { Component, proxy, t, useProps } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { rpc } from "@web/core/network/rpc";

export const RATING = Object.freeze({
    GOOD: 5,
    OK: 3,
    BAD: 1,
});

/**
 * @typedef {Object} Props
 * @property {Function} [onClickClose]
 * @property {import("models").Thread}
 * @extends {Component<Props, Env>}
 */
export class FeedbackPanel extends Component {
    static template = "im_livechat.FeedbackPanel";
    static components = { TranscriptSender };

    STEP = Object.freeze({
        RATING: "rating",
        THANKS: "thanks",
    });
    RATING = RATING;

    setup() {
        this.store = useService("mail.store");
        this.state = proxy({
            step: this.STEP.RATING,
            rating: null,
            feedback: "",
        });
        this.props = useProps({
            onClickClose: t.function().optional(),
            thread: t.instanceOf(this.store["mail.thread"]),
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
        const link = this.props.thread.channel?.livechat_channel_id?.review_link;
        if (this.state.rating === this.RATING.GOOD && link) {
            window.open(link, "_blank", "noopener");
        }
    }
}
