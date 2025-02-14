import { Component, onMounted, onWillUnmount } from "@odoo/owl";
// import { Dialog } from "@web/core/dialog/dialog";
import { BottomSheet } from "@web/core/bottom_sheet/bottom_sheet";
import { useMessageActions } from "./message_actions";
import { useChildRef, useService } from "@web/core/utils/hooks";

export class MessageActionMenuMobile extends Component {
    static components = { BottomSheet };
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
        this.store = useService("mail.store");
        this.bottomSheetRootRef = useChildRef();
        this.messageActions = useMessageActions();
        // this.onClickModal = this.onClickModal.bind(this);
        // onMounted(() => {
        //     this.modalRef.el.addEventListener("click", this.onClickModal);
        // });
        // onWillUnmount(() => {
        //     this.modalRef.el.removeEventListener("click", this.onClickModal);
        // });
    }

    // onClickModal() {
    //     this.props.close?.();
    // }

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
