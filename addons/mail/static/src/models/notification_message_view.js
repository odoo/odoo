/** @odoo-module **/

import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
import { useUpdateToModel } from "@mail/component_hooks/use_update_to_model";
import { attr, one, Model } from "@mail/model";

Model({
    name: "NotificationMessageView",
    template: "mail.NotificationMessageView",
    componentSetup() {
        useComponentToModel({ fieldName: "component" });
        useUpdateToModel({ methodName: "onComponentUpdate" });
    },
    recordMethods: {
        onComponentUpdate() {
            if (!this.exists()) {
                return;
            }
            if (
                this.messageListViewItemOwner.threadViewOwnerAsLastMessageListViewItem &&
                this.messageListViewItemOwner.isPartiallyVisible()
            ) {
                this.messageListViewItemOwner.threadViewOwnerAsLastMessageListViewItem.handleVisibleMessage(
                    this.message
                );
            }
        },
    },
    fields: {
        component: attr(),
        message: one("Message", {
            inverse: "notificationMessageViews",
            related: "messageListViewItemOwner.message",
            required: true,
        }),
        messageListViewItemOwner: one("MessageListViewItem", {
            identifying: true,
            inverse: "notificationMessageView",
        }),
    },
});
