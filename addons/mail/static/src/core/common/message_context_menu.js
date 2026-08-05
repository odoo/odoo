import { ActionList } from "./action_list";
import { useMessageActions } from "./message_actions";

import { propSignal, usePropsPlus } from "@mail/utils/common/hooks";

import { Component, t } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";

export class MessageContextMenu extends Component {
    static template = "mail.MessageContextMenu";
    static components = { ActionList, Dropdown };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = usePropsPlus({
            /** Anchor element, owned by the parent and bound here with `t-ref`. */
            anchorRef: propSignal(t.instanceOf(HTMLElement)),
            dropdownState: t.instanceOf(DropdownState),
            message: t.instanceOf(this.store["mail.message"]),
            thread: t.instanceOf(this.store["mail.thread"]).optional(),
        });
        this.messageActions = useMessageActions({
            message: () => this.props.message,
            reactionAnchorRef: this.props.anchorRef,
            thread: () => this.props.thread,
        });
    }
}
