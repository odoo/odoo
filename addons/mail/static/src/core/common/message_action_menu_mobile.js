import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useMessageActions } from "./message_actions";
import { useChildRef, useService } from "@web/core/utils/hooks";

export class MessageActionMenuMobile extends Component {
    static components = { Dialog };
    static props = [
        "message",
        "close?",
        "thread?",
        "isFirstMessage?",
        "messageToReplyTo?",
        "openReactionMenu?",
        "state",
    ];
    static template = "mail.MessageActionMenuMobile";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.modalRef = useChildRef();
        this.messageActions = useMessageActions();
        this.onClickModal = this.onClickModal.bind(this);
        onMounted(() => {
            this.modalRef.el.addEventListener("click", this.onClickModal);
        });
        onWillUnmount(() => {
            this.modalRef.el.removeEventListener("click", this.onClickModal);
        });
    }

    onClickModal() {
        this.props.close?.();
    }

    get message() {
        return this.props.message;
    }

    get state() {
        return this.props.state;
    }

    async onClickAction(action) {
        const success = await action.onClick();
        if (action.mobileCloseAfterClick && (success || success === undefined)) {
            this.props.close?.();
        }
    }

    openReactionMenu() {
        return this.props.openReactionMenu?.();
    }
}
