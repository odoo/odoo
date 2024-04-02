import { Component } from "@odoo/owl";
import { Typing } from "@mail/discuss/typing/common/typing";

export class ImStatus extends Component {
    static props = ["persona", "className?", "style?", "thread?"];
    static template = "mail.ImStatus";
    static defaultProps = { className: "", style: "" };
    static components = { Typing };
}
