import { Component, signal } from "@odoo/owl";
import { useForwardRefToParent, useService } from "@web/core/utils/hooks";
import { ActionList } from "./action_list";
import { useMessageActions } from "./message_actions";
import { Dropdown } from "@web/core/dropdown/dropdown";

export class MessageContextMenu extends Component {
    static template = "mail.MessageContextMenu";
    static components = { ActionList, Dropdown };
    static props = ["anchorRef", "dropdownState", "message", "thread?"];

    anchorRef = signal(null);

    setup() {
        super.setup();
        useForwardRefToParent(this.anchorRef, "anchorRef");
        this.store = useService("mail.store");
        this.isMessageContextMenu = true;
        this.messageActions = useMessageActions({
            message: () => this.props.message,
            thread: () => this.props.thread,
        });
    }
}
