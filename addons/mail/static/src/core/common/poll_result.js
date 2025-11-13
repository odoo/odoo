import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {import("models").Poll} poll
 * @extends {Component<Props, Env>}
 */
export class PollResult extends Component {
    static template = "mail.PollResult";
    static props = { poll: Object };

    onClickViewPoll() {
        this.env.messageHighlight.highlightMessage(
            this.props.poll.start_message_id,
            this.props.poll.start_message_id.thread
        );
    }
}
