/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
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
            this.message.updateContent({ body: '' });
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
            this.message.replyTo();
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

        _computeIsReactionPopoverOpened() {
            return Boolean(
                this.reactionPopoverRef &&
                this.reactionPopoverRef.comp &&
                this.reactionPopoverRef.comp.state.displayed
            );
        }
    }

    MessageActionList.fields = {
        /**
         * States whether the reaction popover is currently opened.
         */
        isReactionPopoverOpened: attr({
            compute: '_computeIsReactionPopoverOpened',
        }),
        message: one2one('mail.message', {
            inverse: 'actionList'
        }),
        /**
         * States the reference to the reaction popover component (if any).
         */
        reactionPopoverRef: attr(),
        /**
         * Whether to show the message delete-confirm dialog
         */
        showDeleteConfirm: attr({
            default: false,
        }),
    };

    MessageActionList.modelName = 'mail.message_action_list';

    return MessageActionList;
}

registerNewModel('mail.message_action_list', factory);
