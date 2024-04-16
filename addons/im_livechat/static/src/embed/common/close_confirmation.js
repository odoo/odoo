import { Component, useRef, useEffect } from "@odoo/owl";

export class CloseConfirmation extends Component {
    static template = "im_livechat.closeConfirmation";
    static props = ["onCloseConfirmationDialog", "onClickLeaveConversation"];

    setup() {
        this.confirmationDialogRef = useRef("closeConfirmation");
        useEffect(
            () => {
                if (this.confirmationDialogRef.el) {
                    this.confirmationDialogRef.el.focus();
                }
            },
            () => [this.confirmationDialogRef.el]
        );
    }

    onKeydown(ev) {
        if (ev.key === "Escape") {
            this.props.onCloseConfirmationDialog();
        } else if (ev.key === "Enter") {
            this.props.onClickLeaveConversation();
        }
    }

    onClick(ev) {
        const targetClass = ev.target.classList;
        switch (true) {
            case targetClass.contains("o-livechat-closeConfirmation-overlay"):
            case targetClass.contains("btn-close"):
                this.props.onCloseConfirmationDialog();
                break;
            case targetClass.contains("o-livechat-closeConfirmation-leave"):
                this.props.onClickLeaveConversation();
                break;
            default:
                break;
        }
    }
}
