/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageActionList',
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeActionDelete() {
            if (this.message && this.message.canBeDeleted) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeActionEdit() {
            if (this.message && this.message.canBeDeleted) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeActionMarkAsRead() {
            if (
                this.messaging && this.messaging.inbox &&
                this.messageView && this.messageView.messageListViewMessageViewItemOwner && this.messageView.messageListViewMessageViewItemOwner.messageListViewOwner.threadViewOwner.thread &&
                this.messageView.messageListViewMessageViewItemOwner.messageListViewOwner.threadViewOwner.thread === this.messaging.inbox.thread
            ) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeActionReaction() {
            if (this.message && this.message.hasReactionIcon) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeActionReplyTo() {
            if (
                this.messaging && this.messaging.inbox &&
                this.message && !this.message.isTemporary && !this.message.isTransient &&
                this.messageView && this.messageView.messageListViewMessageViewItemOwner && this.messageView.messageListViewMessageViewItemOwner.messageListViewOwner.threadViewOwner.thread && (
                    this.messageView.messageListViewMessageViewItemOwner.messageListViewOwner.threadViewOwner.thread === this.messaging.inbox.thread ||
                    this.messageView.messageListViewMessageViewItemOwner.messageListViewOwner.threadViewOwner.thread.channel
                )
            ) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeActionToggleCompact() {
            if (this.messageView.isInChatWindow && (this.actionsWithoutCompactCount > this.compactThreshold)) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeActionToggleStar() {
            if (this.message && this.message.canStarBeToggled) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeFirstActionView() {
            if (this.actionViewsCount === 0) {
                return clear();
            }
            return this.messageActionViews[0];
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeLastActionView() {
            if (this.actionViewsCount === 0) {
                return clear();
            }
            return this.messageActionViews[this.actionViewsCount - 1];
        },
        _sortMessageActionViews() {
            return [
                ['smaller-first', 'messageAction.sequence'],
            ];
        }
    },
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
            compute: '_computeActionDelete',
            inverse: 'messageActionListOwnerAsDelete',
            isCausal: true,
        }),
        actionEdit: one('MessageAction', {
            compute: '_computeActionEdit',
            inverse: 'messageActionListOwnerAsEdit',
            isCausal: true,
        }),
        actionMarkAsRead: one('MessageAction', {
            compute: '_computeActionMarkAsRead',
            inverse: 'messageActionListOwnerAsMarkAsRead',
            isCausal: true,
        }),
        actionReaction: one('MessageAction', {
            compute: '_computeActionReaction',
            inverse: 'messageActionListOwnerAsReaction',
            isCausal: true,
        }),
        actionReplyTo: one('MessageAction', {
            compute: '_computeActionReplyTo',
            inverse: 'messageActionListOwnerAsReplyTo',
            isCausal: true,
        }),
        actionToggleCompact: one('MessageAction', {
            compute: '_computeActionToggleCompact',
            inverse: 'messageActionListOwnerAsToggleCompact',
            isCausal: true,
        }),
        actionToggleStar: one('MessageAction', {
            compute: '_computeActionToggleStar',
            inverse: 'messageActionListOwnerAsToggleStar',
            isCausal: true,
        }),
        compactThreshold: attr({
            default: 2,
            readonly: true,
        }),
        firstActionView: one('MessageActionView', {
            compute: '_computeFirstActionView',
            readonly: true,
        }),
        isCompact: attr({
            default: true,
        }),
        lastActionView: one('MessageActionView', {
            compute: '_computeLastActionView',
            readonly: true,
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
            readonly: true,
            related: 'messageActions.messageActionView',
            sort: '_sortMessageActionViews',
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
