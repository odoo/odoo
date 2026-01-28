import { Component } from "@odoo/owl";
import { Typing } from "@mail/discuss/typing/common/typing";
import { attClassObjectToString } from "@mail/utils/common/format";

export class ImStatus extends Component {
    static props = ["persona?", "className?", "style?", "member?", "slots?", "size?", "typing?"];
    static template = "mail.ImStatus";
    static defaultProps = { className: "", style: "", size: "lg", typing: true };
    static components = { Typing };

    setup() {
        super.setup();
        this.attClassObjectToString = attClassObjectToString;
    }

    get persona() {
        return this.props.persona ?? this.props.member?.persona;
    }

    get showTypingIndicator() {
        return this.props.typing && this.props.member?.isTyping;
    }

    get attr() {
        return { class: this.class, style: this.props.style };
    }

    get class() {
        return attClassObjectToString({
            [`o-mail-ImStatus d-flex ${this.props.className}`]: true,
            "o-fs-small": this.persona?.im_status !== "bot",
            "rounded-circle bg-transparent": !this.showTypingIndicator,
            "rounded-pill": this.showTypingIndicator,
        });
    }
}
