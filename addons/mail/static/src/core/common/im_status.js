import { Component } from "@odoo/owl";
import { Typing } from "@mail/discuss/typing/common/typing";

export class ImStatus extends Component {
    static props = ["partner?", "guest?", "className?", "style?", "member?", "slots?", "size?"];
    static template = "mail.ImStatus";
    static defaultProps = { className: "", style: "", size: "lg" };
    static components = { Typing };

    get im_status() {
        return this.props.partner?.im_status || this.props.guest?.im_status || this.props.member?.im_status;
    }
}
