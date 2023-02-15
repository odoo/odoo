/** @odoo-module **/

import { attr, clear, many, one, Model } from "@mail/model";

Model({
    name: "MessageActionList",
    template: "mail.MessageActionList",
    fields: {
        actionViewsCount: attr({
            default: 0,
            readonly: true,
            sum: "messageActionViews.actionViewCounterContribution",
        }),
        actionsWithoutCompactCount: attr({
            default: 0,
            readonly: true,
            sum: "messageActions.isNonCompactActionContribution",
        }),
        actionDelete: one("MessageAction", {
            inverse: "messageActionListOwnerAsDelete",
            compute() {
                if (this.message && this.message.canBeDeleted) {
                    return {};
                }
                return clear();
            },
        }),
        actionEdit: one("MessageAction", {
            inverse: "messageActionListOwnerAsEdit",
            compute() {
                if (this.message && this.message.canBeDeleted) {
                    return {};
                }
                return clear();
            },
        }),
        actionMarkAsRead: one("MessageAction", {
            inverse: "messageActionListOwnerAsMarkAsRead",
            compute() {
                if (
                    this.messaging &&
                    this.messaging.inbox &&
                    this.messageView &&
                    this.messageView.messageListViewItemOwner &&
                    this.messageView.messageListViewItemOwner.messageListViewOwner.threadViewOwner
                        .thread &&
                    this.messageView.messageListViewItemOwner.messageListViewOwner.threadViewOwner
                        .thread === this.messaging.inbox.thread
                ) {
                    return {};
                }
                return clear();
            },
        }),
        actionReaction: one("MessageAction", {
            inverse: "messageActionListOwnerAsReaction",
            compute() {
                if (this.message && this.message.hasReactionIcon) {
                    return {};
                }
                return clear();
            },
        }),
        actionReplyTo: one("MessageAction", {
            inverse: "messageActionListOwnerAsReplyTo",
            compute() {
                if (
                    this.messaging &&
                    this.messaging.inbox &&
                    this.message &&
                    !this.message.isTemporary &&
                    !this.message.isTransient &&
                    this.messageView &&
                    this.messageView.messageListViewItemOwner &&
                    this.messageView.messageListViewItemOwner.messageListViewOwner.threadViewOwner
                        .thread &&
                    (this.messageView.messageListViewItemOwner.messageListViewOwner.threadViewOwner
                        .thread === this.messaging.inbox.thread ||
                        this.messageView.messageListViewItemOwner.messageListViewOwner
                            .threadViewOwner.thread.channel)
                ) {
                    return {};
                }
                return clear();
            },
        }),
        actionToggleCompact: one("MessageAction", {
            inverse: "messageActionListOwnerAsToggleCompact",
            compute() {
                if (
                    this.messageView.isInChatWindow &&
                    this.actionsWithoutCompactCount > this.compactThreshold
                ) {
                    return {};
                }
                return clear();
            },
        }),
        actionToggleStar: one("MessageAction", {
            inverse: "messageActionListOwnerAsToggleStar",
            compute() {
                if (this.message && this.message.canStarBeToggled) {
                    return {};
                }
                return clear();
            },
        }),
        compactThreshold: attr({ default: 2, readonly: true }),
        firstActionView: one("MessageActionView", {
            compute() {
                if (this.actionViewsCount === 0) {
                    return clear();
                }
                return this.messageActionViews[0];
            },
        }),
        isCompact: attr({ default: true }),
        lastActionView: one("MessageActionView", {
            compute() {
                if (this.actionViewsCount === 0) {
                    return clear();
                }
                return this.messageActionViews[this.actionViewsCount - 1];
            },
        }),
        /**
         * States the message on which this action message list operates.
         */
        message: one("Message", { related: "messageView.message" }),
        messageActions: many("MessageAction", {
            inverse: "messageActionListOwner",
            isCausal: true,
        }),
        messageActionViews: many("MessageActionView", {
            related: "messageActions.messageActionView",
            sort: [["smaller-first", "messageAction.sequence"]],
        }),
        /**
         * States the message view that controls this message action list.
         */
        messageView: one("MessageView", { identifying: true, inverse: "messageActionList" }),
    },
});
