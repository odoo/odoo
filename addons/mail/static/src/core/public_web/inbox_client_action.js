import { Discuss } from "@mail/core/public_web/discuss";

import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class InboxClientAction extends Component {
    static components = { Discuss };
    static props = ["*"];
    static template = "mail.InboxClientAction";

    async setup() {
        super.setup();
        this.store = useService("mail.store");
        const activeThread = await this.store.Thread.getOrFetch({ model: 'mail.box', id: 'inbox' });
        activeThread.setAsDiscussThread(false);
    }

}

registry.category("actions").add("mail.action_inbox", InboxClientAction);
