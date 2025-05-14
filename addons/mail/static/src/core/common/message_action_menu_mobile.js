import { Component } from "@odoo/owl";
import { useMessageActions } from "./message_actions";
import { useService } from "@web/core/utils/hooks";
import { BottomSheet } from "@web/core/bottom_sheet/bottom_sheet";

export class MessageActionMenuMobile extends Component {
    static components = { BottomSheet };
    static props = [
        "message",
        "close?",
        "thread?",
        "isFirstMessage?",
        "openReactionMenu?",
        "state",
    ];
    static template = "mail.MessageActionMenuMobile";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.messageActions = useMessageActions();
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
            // Small delay to ensure any state changes have processed
            setTimeout(() => {
                this.props.close?.();
            }, 50);
        }
    }

    openReactionMenu() {
        return this.props.openReactionMenu?.();
    }
}
