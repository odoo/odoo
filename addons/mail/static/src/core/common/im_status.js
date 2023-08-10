/* @odoo-module */

import { Component } from "@odoo/owl";
import { Typing } from "@mail/discuss/typing/common/typing";
import { useTypingService } from "@mail/discuss/typing/common/typing_service";

export class ImStatus extends Component {
    static props = ["persona", "className?", "style?", "thread?"];
    static template = "mail.ImStatus";
    static defaultProps = { className: "", style: "" };
    static components = { Typing };
    setup() {
        this.typingService = useTypingService();
    }
}
