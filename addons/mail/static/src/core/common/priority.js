import { Component, props, types } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class Priority extends Component {
    static template = "mail.Priority";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = props({
            thread: types.instanceOf(this.store["mail.thread"].Class),
        });
    }

    get priorityDefinition() {
        return Object.fromEntries(this.props.thread.priority_definition);
    }

    get priority() {
        return Number(this.props.thread.priority);
    }

    get label() {
        return this.priorityDefinition[this.priority];
    }
}
