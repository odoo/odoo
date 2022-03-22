/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

const { Ref } = owl;

registerModel({
    name: 'PopoverView',
    identifyingFields: [['composerViewOwnerAsEmoji', 'messageActionListOwnerAsReaction', 'threadViewTopbarOwnerAsInvite']],
    lifecycleHooks: {
        _created() {
            document.addEventListener('click', this._onClickCaptureGlobal, true);
        },
        _willDelete() {
            document.removeEventListener('click', this._onClickCaptureGlobal, true);
        },
    },
    recordMethods: {
        /**
         * Returns whether the given html element is inside the component
         * of this popover view.
         *
         * @param {Element} element
         * @returns {boolean}
         */
        contains(element) {
            return Boolean(this.component && this.component.root.el.contains(element));
        },
        /**
         * @private
         * @returns {Ref}
         */
        _computeAnchorRef() {
            if (this.threadViewTopbarOwnerAsInvite) {
                return this.threadViewTopbarOwnerAsInvite.inviteButtonRef;
            }
            if (this.composerViewOwnerAsEmoji) {
                return this.composerViewOwnerAsEmoji.buttonEmojisRef;
            }
            if (this.messageActionListOwnerAsReaction) {
                return this.messageActionListOwnerAsReaction.actionReactionRef;
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChannelInvitationForm() {
            if (this.threadViewTopbarOwnerAsInvite) {
                return insertAndReplace();
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeContent() {
            if (this.channelInvitationForm) {
                return replace(this.channelInvitationForm);
            }
            if (this.emojiListView) {
                return replace(this.emojiListView);
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeContentClassName() {
            if (this.channelInvitationForm) {
                return 'o_PopoverView_channelInvitationForm';
            }
            if (this.emojiListView) {
                return 'o_PopoverView_emojiList';
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeContentComponentName() {
            if (this.channelInvitationForm) {
                return 'ChannelInvitationForm';
            }
            if (this.emojiListView) {
                return 'EmojiList';
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeEmojiListView() {
            if (this.composerViewOwnerAsEmoji) {
                return insertAndReplace();
            }
            if (this.messageActionListOwnerAsReaction) {
                return insertAndReplace();
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computePosition() {
            if (this.threadViewTopbarOwnerAsInvite) {
                return 'bottom';
            }
            if (this.composerViewOwnerAsEmoji) {
                return 'top';
            }
            if (this.messageActionListOwnerAsReaction) {
                return 'top';
            }
            return clear();
        },
        /**
         * Closes the popover when clicking outside, if appropriate.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClickCaptureGlobal(ev) {
            if (!this.component || !this.component.root.el) {
                return;
            }
            if (this.anchorRef && this.anchorRef.el && this.anchorRef.el.contains(ev.target)) {
                return;
            }
            if (this.component.root.el.contains(ev.target)) {
                return;
            }
            this.delete();
        },
    },
    fields: {
        /**
         * HTML element that is used as anchor position for this popover view.
         */
        anchorRef: attr({
            compute: '_computeAnchorRef',
            required: true,
        }),
        /**
         * The record that represents the content inside the popover view.
         */
        channelInvitationForm: one('ChannelInvitationForm', {
            compute: '_computeChannelInvitationForm',
            inverse: 'popoverViewOwner',
            isCausal: true,
            readonly: true,
        }),
        /**
         * States the OWL component of this popover view.
         */
        component: attr(),
        /**
         * If set, this popover view is owned by a composer view.
         */
        composerViewOwnerAsEmoji: one('ComposerView', {
            inverse: 'emojisPopoverView',
            readonly: true,
        }),
        /**
         * Determines the record that is content of this popover view.
         */
        content: one('Model', {
            compute: '_computeContent',
            required: true,
        }),
        /**
         * Determines the class name for the component
         * that is content of this popover view.
         */
        contentClassName: attr({
            compute: '_computeContentClassName',
            default: '',
        }),
        /**
         * Determines the component name of the content.
         */
        contentComponentName: attr({
            compute: '_computeContentComponentName',
            default: '',
            required: true,
        }),
        /**
         * If set, the content of this popover view is a list of emojis.
         */
        emojiListView: one('EmojiListView', {
            compute: '_computeEmojiListView',
            inverse: 'popoverViewOwner',
            isCausal: true,
            readonly: true,
        }),
        /**
         * If set, this popover view is owned by a message action list.
         */
        messageActionListOwnerAsReaction: one('MessageActionList', {
            inverse: 'reactionPopoverView',
            readonly: true,
        }),
        /**
         * Position of the popover view relative to its anchor point.
         * Valid values: 'top', 'right', 'bottom', 'left'
         */
        position: attr({
            compute: '_computePosition',
            default: 'top',
        }),
        /**
         * If set, this popover view is owned by a thread view topbar record.
         */
        threadViewTopbarOwnerAsInvite: one('ThreadViewTopbar', {
            inverse: 'invitePopoverView',
            readonly: true,
        }),
    },
});
