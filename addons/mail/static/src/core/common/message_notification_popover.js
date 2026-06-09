import { Component, props, types } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class MessageNotificationPopover extends Component {
    static template = "mail.MessageNotificationPopover";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = props({
            message: types.instanceOf(this.store["mail.message"].Class),
        });
    }
}
