import { Component, onMounted, useRef } from "@odoo/owl";

export class CloseConfirmation extends Component {
    static template = "im_livechat.CloseConfirmation";
    static props = ["onCloseConfirmationDialog", "onClickLeaveConversation"];

    setup() {
        this.root = useRef("root");
        onMounted(() => this.root.el.focus());
    }

    onKeydown(ev) {
        if (ev.key === "Escape") {
            this.props.onCloseConfirmationDialog();
        } else if (ev.key === "Enter") {
            this.props.onClickLeaveConversation();
        }
    }
}
