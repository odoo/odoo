import { propComputed } from "@mail/utils/common/hooks";

import { Component, t } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class Priority extends Component {
    static template = "mail.Priority";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.thread = propComputed("thread", t.instanceOf(this.store["mail.thread"]));
    }

    get priorityDefinition() {
        return Object.fromEntries(this.thread().priority_definition);
    }

    get priority() {
        return Number(this.thread().priority);
    }

    get label() {
        return this.priorityDefinition[this.priority];
    }
}
