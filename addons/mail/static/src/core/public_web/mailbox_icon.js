import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class MailboxIcon extends Component {
    static template = "mail.MailboxIcon";
    static props = ["mailbox", "size?"];

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }
}
