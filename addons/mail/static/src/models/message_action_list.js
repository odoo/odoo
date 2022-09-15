/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageActionList',
    fields: {
        actionViewsCount: attr({
            default: 0,
            readonly: true,
            sum: 'messageActionViews.actionViewCounterContribution',
        }),
        actionsWithoutCompactCount: attr({
            default: 0,
            readonly: true,
            sum: 'messageActions.isNonCompactActionContribution',
        }),
        actionDelete: one('MessageAction', {
            compute() {
                if (this.message && this.message.canBeDeleted) {
                    return {};
                }
                return clear();
            },
            inverse: 'messageActionListOwnerAsDelete',
        }),
        actionEdit: one('MessageAction', {
            compute() {
                if (this.message && this.message.canBeDeleted) {
                    return {};
                }
                return clear();
            },
            inverse: 'messageActionListOwnerAsEdit',
        }),
        actionMarkAsRead: one('MessageAction', {
            compute() {
                if (
                    this.messaging && this.messaging.inbox &&
                    this.messageView && this.messageView.messageListViewItemOwner && this.messageView.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread &&
                    this.messageView.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread === this.messaging.inbox.thread
                ) {
                    return {};
                }
                return clear();
            },
            inverse: 'messageActionListOwnerAsMarkAsRead',
        }),
        actionReaction: one('MessageAction', {
            compute() {
                if (this.message && this.message.hasReactionIcon) {
                    return {};
                }
                return clear();
            },
            inverse: 'messageActionListOwnerAsReaction',
        }),
        actionReplyTo: one('MessageAction', {
            compute() {
                if (
                    this.messaging && this.messaging.inbox &&
                    this.message && !this.message.isTemporary && !this.message.isTransient &&
                    this.messageView && this.messageView.messageListViewItemOwner && this.messageView.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread && (
                        this.messageView.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread === this.messaging.inbox.thread ||
                        this.messageView.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread.channel
                    )
                ) {
                    return {};
                }
                return clear();
            },
            inverse: 'messageActionListOwnerAsReplyTo',
        }),
        actionToggleCompact: one('MessageAction', {
            compute() {
                if (this.messageView.isInChatWindow && (this.actionsWithoutCompactCount > this.compactThreshold)) {
                    return {};
                }
                return clear();
            },
            inverse: 'messageActionListOwnerAsToggleCompact',
        }),
        actionToggleStar: one('MessageAction', {
            compute() {
                if (this.message && this.message.canStarBeToggled) {
                    return {};
                }
                return clear();
            },
            inverse: 'messageActionListOwnerAsToggleStar',
        }),
        compactThreshold: attr({
            default: 2,
            readonly: true,
        }),
        firstActionView: one('MessageActionView', {
            compute() {
                if (this.actionViewsCount === 0) {
                    return clear();
                }
                return this.messageActionViews[0];
            },
        }),
        isCompact: attr({
            default: true,
        }),
        lastActionView: one('MessageActionView', {
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
        message: one('Message', {
            related: 'messageView.message',
        }),
        messageActions: many('MessageAction', {
            inverse: 'messageActionListOwner',
            isCausal: true,
        }),
        messageActionViews: many('MessageActionView', {
            related: 'messageActions.messageActionView',
            sort() {
                return [
                    ['smaller-first', 'messageAction.sequence'],
                ];
            },
        }),
        /**
         * States the message view that controls this message action list.
         */
        messageView: one('MessageView', {
            identifying: true,
            inverse: 'messageActionList',
        }),
    },
});
