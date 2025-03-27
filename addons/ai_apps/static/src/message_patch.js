import { Message } from "@mail/core/common/message";
import { MessageActionMenuMobile } from "@mail/core/common/message_action_menu_mobile";
import { patch } from "@web/core/utils/patch";
import { isMobileOS } from "@web/core/browser/feature_detection";


patch(Message.prototype, {
    openMobileActions(ev) {
        if (this.props.thread.channel_type !== "ai_composer") {
            super.openMobileActions(ev);
        }
        if (!isMobileOS()) {
            return;
        }
        ev?.stopPropagation();
        this.state.actionMenuMobileOpen = true;
        this.dialog.add(
            MessageActionMenuMobile,
            {
                message: this.props.message,
                thread: this.props.thread,
                isFirstMessage: this.props.isFirstMessage,
                messageToReplyTo: this.props.messageToReplyTo,
                openReactionMenu: () => this.openReactionMenu(),
                state: this.state,
                insertToEditor: (content) => this.env.specialActions['insert'](content),
            },
            { context: this, onClose: () => (this.state.actionMenuMobileOpen = false) }
        );
    },
    async copyMessageText() {
        let notification = _t("Message Copied!");
        let type = "info";
        try {
            await browser.navigator.clipboard.writeText(this.message.body);
        } catch {
            notification = _t("Message Copy Failed (Permission denied?)!");
            type = "danger";
        }
        this.store.env.services.notification.add(notification, { type });
    }
});
