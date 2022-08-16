/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'MessageActionList',
    recordMethods: {
        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            markEventHandled(ev, 'MessageActionList.Click');
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickDelete(ev) {
            this.update({ deleteConfirmDialog: insertAndReplace() });
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
         onClickEdit(ev) {
            this.messageView.startEditing();
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickMarkAsRead(ev) {
            this.message.markAsRead();
        },
        /**
         * Handles click on the reaction icon.
         */
        onClickActionReaction() {
            if (!this.reactionPopoverView) {
                this.update({ reactionPopoverView: insertAndReplace() });
            } else {
                this.update({ reactionPopoverView: clear() });
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickReaction(ev) {
            this.message.addReaction(ev.currentTarget.dataset.unicode);
            this.update({ reactionPopoverView: clear() });
        },
        /**
         * Opens the reply composer for this message (or closes it if it was
         * already opened).
         *
         * @private
         * @param {MouseEvent} ev
         */
        onClickReplyTo(ev) {
            markEventHandled(ev, 'MessageActionList.replyTo');
            this.messageView.replyTo();
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickToggleCompact(ev) {
            this.update({ isCompact: !this.isCompact });
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickToggleStar(ev) {
            this.message.toggleStar();
        },
        /**
         * @private
         * @returns {integer|FieldCommand}
         */
        _computeActionsCount() {
            if (this.message){
                const actions = [
                    this.hasMarkAsReadIcon,
                    this.hasReplyIcon,
                    this.message.canBeDeleted,
                    this.message.canBeDeleted,
                    this.message.canStarBeToggled,
                    this.message.hasReactionIcon,
                ]
                return actions.filter(Boolean).length;
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeAddReactionText() {
            return this.env._t("Add a Reaction");
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasCompactIcon() {
            const COMPACT_THRESHOLD = 2;
            const viewer = this.messageView && this.messageView.messageListViewMessageViewItemOwner && this.messageView.messageListViewMessageViewItemOwner.messageListViewOwner.threadViewOwner.threadViewer;
            if (viewer && viewer.chatWindow) {
                return this.actionsCount > COMPACT_THRESHOLD;
            }
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasMarkAsReadIcon() {
            return Boolean(
                this.messaging && this.messaging.inbox &&
                this.messageView && this.messageView.messageListViewMessageViewItemOwner && this.messageView.messageListViewMessageViewItemOwner.messageListViewOwner.threadViewOwner.thread &&
                this.messageView.messageListViewMessageViewItemOwner.messageListViewOwner.threadViewOwner.thread === this.messaging.inbox.thread
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasReplyIcon() {
            return Boolean(
                this.messaging && this.messaging.inbox &&
                this.message && !this.message.isTemporary && !this.message.isTransient &&
                this.messageView && this.messageView.messageListViewMessageViewItemOwner && this.messageView.messageListViewMessageViewItemOwner.messageListViewOwner.threadViewOwner.thread && (
                    this.messageView.messageListViewMessageViewItemOwner.messageListViewOwner.threadViewOwner.thread === this.messaging.inbox.thread ||
                    this.messageView.messageListViewMessageViewItemOwner.messageListViewOwner.threadViewOwner.thread.channel
                )
            );
        },
    },
    fields: {
        /**
         * States the reference to the reaction action in the component.
         */
        actionReactionRef: attr(),
        actionsCount: attr({
            compute: '_computeActionsCount',
            readonly: true,
        }),
        addReactionText: attr({
            compute: '_computeAddReactionText',
        }),
        deleteConfirmDialog: one('Dialog', {
            inverse: 'messageActionListOwnerAsDeleteConfirm',
            isCausal: true,
        }),
        hasCompactIcon: attr({
            compute: '_computeHasCompactIcon',
            readonly: true,
        }),
        /**
         * Determines whether this message action list has mark as read icon.
         */
        hasMarkAsReadIcon: attr({
            compute: '_computeHasMarkAsReadIcon',
        }),
        /**
         * Determines whether this message action list has a reply icon.
         */
        hasReplyIcon: attr({
            compute: '_computeHasReplyIcon',
        }),
        isCompact: attr({
            default: true,
        }),
        /**
         * States the message on which this action message list operates.
         */
        message: one('Message', {
            related: 'messageView.message',
        }),
        /**
         * States the message view that controls this message action list.
         */
        messageView: one('MessageView', {
            identifying: true,
            inverse: 'messageActionList',
            readonly: true,
            required: true,
        }),
        /**
         * Determines the reaction popover that is active on this message action list.
         */
        reactionPopoverView: one('PopoverView', {
            inverse: 'messageActionListOwnerAsReaction',
            isCausal: true,
        }),
    },
});
