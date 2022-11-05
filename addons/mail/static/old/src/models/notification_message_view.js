/** @odoo-module **/

import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
import { useUpdateToModel } from "@mail/component_hooks/use_update_to_model";
import { registerModel } from "@mail/model/model_core";
import { attr, one } from "@mail/model/model_field";

registerModel({
    name: "NotificationMessageView",
    template: "mail.NotificationMessageView",
    templateGetter: "notificationMessageView",
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
