import { ActionList } from "./action_list";
import { useMessageActions } from "./message_actions";

import { Component, computed, props, types } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { useService } from "@web/core/utils/hooks";

export class MessageContextMenu extends Component {
    static template = "mail.MessageContextMenu";
    static components = { ActionList, Dropdown };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            anchorRef: types.signal(types.instanceOf(HTMLElement)),
            dropdownState: types.object(),
            message: types.instanceOf(this.store["mail.message"].Class),
            "thread?": types.instanceOf(this.store["mail.thread"].Class),
        });
        this.messageActions = useMessageActions({
            message: () => this.props.message,
            reactionAnchorRef: computed(() => this.props.anchorRef()),
            thread: () => this.props.thread,
        });
    }
}
