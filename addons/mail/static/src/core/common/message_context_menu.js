import { ActionList } from "./action_list";
import { useMessageActions } from "./message_actions";

import { propSignal } from "@mail/utils/common/hooks";

import { Component, computed, t, useProps } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";

export class MessageContextMenu extends Component {
    static template = "mail.MessageContextMenu";
    static components = { ActionList, Dropdown };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            dropdownState: t.instanceOf(DropdownState),
            message: t.instanceOf(this.store["mail.message"].Class),
            thread: t.instanceOf(this.store["mail.thread"].Class).optional(),
        });
        /** Anchor element, owned by the parent and bound here with `t-ref`. */
        this.anchorRef = propSignal("anchorRef", t.instanceOf(HTMLElement));
        this.messageActions = useMessageActions({
            message: () => this.props.message,
            reactionAnchorRef: computed(() => this.anchorRef()),
            thread: () => this.props.thread,
        });
    }
}
