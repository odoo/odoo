import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class CallConfirmation extends Component {
    static props = ["thread", "close?"];
    static template = "discuss.CallConfirmation";

    setup() {
        super.setup();
        this.ui = useState(useService("ui"));
        this.store = useState(useService("mail.store"));
    }

    proceed() {
        this.store.rtc.toggleCall(this.props.thread);
        this.props.close?.();
    }
}
