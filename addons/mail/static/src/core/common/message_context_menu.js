import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ActionList } from "./action_list";
import { useMessageActions } from "./message_actions";
import { Dropdown } from "@web/core/dropdown/dropdown";

export class MessageContextMenu extends Component {
    static template = "mail.MessageContextMenu";
    static components = { ActionList, Dropdown };
    static props = ["anchorRef", "dropdownState", "message", "thread?"];

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.isMessageContextMenu = true;
        this.messageActions = useMessageActions({
            message: () => this.props.message,
            thread: () => this.props.thread,
        });
    }
}
