/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'MessageActionList',
    identifyingFields: ['messageView'],
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
        onClickConfirmDelete(ev) {
            this.message.updateContent({
                body: '',
                attachment_ids: [],
            });
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickDelete(ev) {
            this.update({ showDeleteConfirm: true });
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
        onClickToggleStar(ev) {
            this.message.toggleStar();
        },
        /**
         * @private
         * @param {CustomEvent} ev
         */
        onDeleteConfirmDialogClosed(ev) {
            this.update({ showDeleteConfirm: false });
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasMarkAsReadIcon() {
            return Boolean(
                this.messaging && this.messaging.inbox &&
                this.messageView && this.messageView.threadView && this.messageView.threadView.thread &&
                this.messageView.threadView.thread === this.messaging.inbox
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
                this.messageView && this.messageView.threadView && this.messageView.threadView.thread && (
                    this.messageView.threadView.thread === this.messaging.inbox ||
                    this.messageView.threadView.thread.model === 'mail.channel'
                )
            );
        },
        /**
         * @private
         * @returns {MessageView}
         */
        _computeMessageViewForDelete() {
            return this.message
                ? insertAndReplace({ message: replace(this.message) })
                : clear();
        },
    },
    fields: {
        /**
         * States the reference to the reaction action in the component.
         */
        actionReactionRef: attr(),
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
            inverse: 'messageActionList',
            readonly: true,
            required: true,
        }),
        /**
         * Determines the message view that this message action list will use to
         * display this message in this delete confirmation dialog.
         */
        messageViewForDelete: one('MessageView', {
            compute: '_computeMessageViewForDelete',
            inverse: 'messageActionListWithDelete',
            isCausal: true,
        }),
        /**
         * Determines the reaction popover that is active on this message action list.
         */
        reactionPopoverView: one('PopoverView', {
            inverse: 'messageActionListOwnerAsReaction',
            isCausal: true,
        }),
        /**
         * Determines whether to show the message delete-confirm dialog.
         */
        showDeleteConfirm: attr({
            default: false,
        }),
    },
});
