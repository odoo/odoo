/** @odoo-module **/

import { clear, one, Model } from "@mail/model";
import { isEventHandled } from "@mail/utils/utils";

Model({
    name: "ChatWindowHeaderView",
    template: "mail.ChatWindowHeaderView",
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            if (!this.exists()) {
                return;
            }
            if (
                isEventHandled(ev, "ChatWindow.onClickCommand") ||
                isEventHandled(ev, "ChatWindow.onClickHideMemberList") ||
                isEventHandled(ev, "ChatWindow.onClickShowMemberList")
            ) {
                return;
            }
            if (!this.chatWindowOwner.isVisible) {
                this.chatWindowOwner.onClickFromChatWindowHiddenMenu(ev);
            } else {
                this.chatWindowOwner.onClickHeader(ev);
            }
        },
    },
    fields: {
        chatWindowOwner: one("ChatWindow", { identifying: true, inverse: "chatWindowHeaderView" }),
        hiddenMenuItem: one("ChatWindowHiddenMenuItemView", { inverse: "chatWindowHeaderView" }),
        threadIconView: one("ThreadIconView", {
            inverse: "chatWindowHeaderViewOwner",
            compute() {
                if (this.chatWindowOwner.thread && this.chatWindowOwner.thread.channel) {
                    return {};
                }
                return clear();
            },
        }),
    },
});
