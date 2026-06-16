import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {import("models").Message} message
 * @property {ReturnType<import('@mail/core/common/message_search_hook').useMessageSearch>} [messageSearch]
 */
export class MessageBodyContent extends Component {
    static template = "mail.Message.bodyContent";
    static props = ["message", "messageSearch?"];

    get body() {
        return (
            this.props.messageSearch?.highlight(this.props.message.richBody) ??
            this.props.message.richBody
        );
    }
}
