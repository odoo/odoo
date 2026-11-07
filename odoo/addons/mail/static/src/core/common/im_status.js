/* @odoo-module */

import { Component, useState } from "@odoo/owl";
import { Typing } from "@mail/discuss/typing/common/typing";
import { useService } from "@web/core/utils/hooks";

export class ImStatus extends Component {
    static props = ["persona", "className?", "style?", "thread?"];
    static template = "mail.ImStatus";
    static defaultProps = { className: "", style: "" };
    static components = { Typing };
    setup() {
        this.typingService = useState(useService("discuss.typing"));
    }
}
