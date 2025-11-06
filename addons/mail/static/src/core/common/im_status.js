import { Component } from "@odoo/owl";
import { Typing } from "@mail/discuss/typing/common/typing";

export class ImStatus extends Component {
    static props = [
        "persona?",
        "className?",
        "style?",
        "member?",
        "slots?",
        "size?",
        "withIsTyping?",
    ];
    static template = "mail.ImStatus";
    static defaultProps = { className: "", style: "", size: "lg", withIsTyping: true };
    static components = { Typing };

    get persona() {
        return this.props.persona ?? this.props.member?.persona;
    }

    get showTypingIndicator() {
        return this.props.withIsTyping && this.props.member?.isTyping;
    }
}
