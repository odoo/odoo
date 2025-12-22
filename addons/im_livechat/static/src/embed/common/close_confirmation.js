import { Component } from "@odoo/owl";
import { useAutofocus } from "@web/core/utils/hooks";

export class CloseConfirmation extends Component {
    static template = "im_livechat.CloseConfirmation";
    static props = ["onCloseConfirmationDialog", "onClickLeaveConversation"];

    setup() {
        useAutofocus({ refName: "root" });
    }

    onKeydown(ev) {
        if (ev.key === "Escape") {
            this.props.onCloseConfirmationDialog();
        } else if (ev.key === "Enter") {
            this.props.onClickLeaveConversation();
        }
    }
}
