/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

function factory(dependencies) {

    class MessageActionList extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            // bind handlers so they can be used in templates
            this.onClick = this.onClick.bind(this);
            this.onClickConfirmDelete = this.onClickConfirmDelete.bind(this);
            this.onClickDelete = this.onClickDelete.bind(this);
            this.onClickEdit = this.onClickEdit.bind(this);
            this.onClickMarkAsRead = this.onClickMarkAsRead.bind(this);
            this.onReactionPopoverOpened = this.onReactionPopoverOpened.bind(this);
            this.onReactionPopoverClosed = this.onReactionPopoverClosed.bind(this);
            this.onClickReplyTo = this.onClickReplyTo.bind(this);
            this.onClickToggleStar = this.onClickToggleStar.bind(this);
            this.onDeleteConfirmDialogClosed = this.onDeleteConfirmDialogClosed.bind(this);
            this.onEmojiSelection = this.onEmojiSelection.bind(this);
        }

        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            markEventHandled(ev, 'MessageActionList.Click');
        }

        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickConfirmDelete(ev) {
            this.message.updateContent({
                body: '',
                attachment_ids: [],
            });
        }

        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickDelete(ev) {
            this.update({ showDeleteConfirm: true });
        }

        /**
         * @private
         * @param {MouseEvent} ev
         */
         onClickEdit(ev) {
            this.messageView.startEditing();
        }

        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickMarkAsRead(ev) {
            this.message.markAsRead();
        }

        /**
         * @private
         * @param {Event} ev
         */
        onReactionPopoverClosed(ev) {
            this.update({ isReactionPopoverOpened: false });
        }

        /**
         * @private
         * @param {Event} ev
         */
        onReactionPopoverOpened(ev) {
            this.update({ isReactionPopoverOpened: true });
        }

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
        }

        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickToggleStar(ev) {
            this.message.toggleStar();
        }

        /**
         * @private
         * @param {CustomEvent} ev
         */
        onDeleteConfirmDialogClosed(ev) {
            this.update({ showDeleteConfirm: false });
        }

        /**
         * Handles `o-emoji-selection` event from the emoji popover.
         *
         * @private
         * @param {CustomEvent} ev
         * @param {Object} ev.detail
         * @param {string} ev.detail.unicode
         */
        onEmojiSelection(ev) {
            this.message.addReaction(ev.detail.unicode);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

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
        }

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
        }

        _computeIsReactionPopoverOpened() {
            return Boolean(
                this.reactionPopoverRef &&
                this.reactionPopoverRef.comp &&
                this.reactionPopoverRef.comp.state.displayed
            );
        }

        /**
         * @private
         * @returns {mail.message_view}
         */
        _computeMessageViewForDelete() {
            return this.message
                ? insertAndReplace({ message: replace(this.message) })
                : clear();
        }

    }

    MessageActionList.fields = {
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
         * States whether the reaction popover is currently opened.
         */
        isReactionPopoverOpened: attr({
            compute: '_computeIsReactionPopoverOpened',
        }),
        /**
         * States the message on which this action message list operates.
         */
        message: many2one('mail.message', {
            related: 'messageView.message',
        }),
        /**
         * States the message view that controls this message action list.
         */
        messageView: one2one('mail.message_view', {
            inverse: 'messageActionList',
            readonly: true,
            required: true,
        }),
        /**
         * Determines the message view that this message action list will use to
         * display this message in this delete confirmation dialog.
         */
        messageViewForDelete: one2one('mail.message_view', {
            compute: '_computeMessageViewForDelete',
            inverse: 'messageActionListWithDelete',
            isCausal: true,
        }),
        /**
         * States the reference to the reaction popover component (if any).
         */
        reactionPopoverRef: attr(),
        /**
         * Determines whether to show the message delete-confirm dialog.
         */
        showDeleteConfirm: attr({
            default: false,
        }),
    };
    MessageActionList.identifyingFields = ['messageView'];
    MessageActionList.modelName = 'mail.message_action_list';

    return MessageActionList;
}

registerNewModel('mail.message_action_list', factory);
