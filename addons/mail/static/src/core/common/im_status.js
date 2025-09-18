import { Typing } from "@mail/discuss/typing/common/typing";
import { Component } from "@odoo/owl";

export class ImStatus extends Component {
    static props = ["persona?", "className?", "style?", "member?", "slots?", "size?"];
    static template = "mail.ImStatus";
    static defaultProps = { className: "", style: "", size: "lg" };
    static components = { Typing };

    get persona() {
        return this.props.persona ?? this.props.member?.persona;
    }
}
