/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'PopoverView',
    identifyingMode: 'xor',
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
            return Boolean(this.component && this.component.root.el && this.component.root.el.contains(element));
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
        activityButtonViewOwnerAsActivityList: one('ActivityButtonView', {
            identifying: true,
            inverse: 'activityListPopoverView',
        }),
        activityListView: one('ActivityListView', {
            compute() {
                return this.activityButtonViewOwnerAsActivityList ? {} : clear();
            },
            inverse: 'popoverViewOwner',
        }),
        activityMarkDonePopoverContentView: one('ActivityMarkDonePopoverContentView', {
            compute() {
                if (this.activityViewOwnerAsMarkDone) {
                    return {};
                }
                return clear();
            },
            inverse: 'popoverViewOwner',
        }),
        activityViewOwnerAsMarkDone: one('ActivityView', {
            identifying: true,
            inverse: 'markDonePopoverView',
        }),
        /**
         * HTML element that is used as anchor position for this popover view.
         */
        anchorRef: attr({
            compute() {
                if (this.activityViewOwnerAsMarkDone) {
                    return this.activityViewOwnerAsMarkDone.markDoneButtonRef;
                }
                if (this.callActionListViewOwnerAsMoreMenu) {
                    return this.callActionListViewOwnerAsMoreMenu.moreButtonRef;
                }
                if (this.callParticipantCardOwner) {
                    return this.callParticipantCardOwner.volumeMenuAnchorRef;
                }
                if (this.threadViewTopbarOwnerAsInvite) {
                    return this.threadViewTopbarOwnerAsInvite.inviteButtonRef;
                }
                if (this.composerViewOwnerAsEmoji) {
                    return this.composerViewOwnerAsEmoji.buttonEmojisRef;
                }
                if (this.activityButtonViewOwnerAsActivityList) {
                    return this.activityButtonViewOwnerAsActivityList.buttonRef;
                }
                if (this.messageActionViewOwnerAsReaction) {
                    return this.messageActionViewOwnerAsReaction.actionRef;
                }
                if (this.messageViewOwnerAsNotificationContent) {
                    return this.messageViewOwnerAsNotificationContent.notificationIconRef;
                }
                return clear();
            },
            required: true,
        }),
        callActionListViewOwnerAsMoreMenu: one('CallActionListView', {
            identifying: true,
            inverse: 'moreMenuPopoverView',
        }),
        callOptionMenuView: one('CallOptionMenu', {
            compute() {
                if (this.callActionListViewOwnerAsMoreMenu) {
                    return {};
                }
                return clear();
            },
            inverse: 'popoverViewOwner',
        }),
        callParticipantCardOwner: one('CallParticipantCard', {
            identifying: true,
            inverse: 'callParticipantCardPopoverView',
        }),
        callParticipantCardPopoverContentView: one('CallParticipantCardPopoverContentView', {
            compute() {
                if (this.callParticipantCardOwner) {
                    return {};
                }
                return clear();
            },
            inverse: 'popoverViewOwner',
        }),
        /**
         * The record that represents the content inside the popover view.
         */
        channelInvitationForm: one('ChannelInvitationForm', {
            compute() {
                if (this.threadViewTopbarOwnerAsInvite) {
                    return {};
                }
                return clear();
            },
            inverse: 'popoverViewOwner',
        }),
        /**
         * States the OWL component of this popover view.
         */
        component: attr(),
        /**
         * If set, this popover view is owned by a composer view.
         */
        composerViewOwnerAsEmoji: one('ComposerView', {
            identifying: true,
            inverse: 'emojisPopoverView',
        }),
        /**
         * Determines the record that is content of this popover view.
         */
        content: one('Record', {
            compute() {
                if (this.activityMarkDonePopoverContentView) {
                    return this.activityMarkDonePopoverContentView;
                }
                if (this.callOptionMenuView) {
                    return this.callOptionMenuView;
                }
                if (this.callParticipantCardPopoverContentView) {
                    return this.callParticipantCardPopoverContentView;
                }
                if (this.channelInvitationForm) {
                    return this.channelInvitationForm;
                }
                if (this.emojiPickerView) {
                    return this.emojiPickerView;
                }
                if (this.activityButtonViewOwnerAsActivityList) {
                    return this.activityListView;
                }
                if (this.messageNotificationPopoverContentView) {
                    return this.messageNotificationPopoverContentView;
                }
                return clear();
            },
            required: true,
        }),
        /**
         * Determines the class name for the component
         * that is content of this popover view.
         */
        contentClassName: attr({
            compute() {
                if (this.channelInvitationForm) {
                    return 'o_PopoverView_channelInvitationForm';
                }
                if (this.emojiPickerView) {
                    return 'o_PopoverView_emojiPickerView';
                }
                return clear();
            },
            default: '',
        }),
        /**
         * Determines the component name of the content.
         */
        contentComponentName: attr({
            compute() {
                if (this.activityMarkDonePopoverContentView) {
                    return 'ActivityMarkDonePopoverContent';
                }
                if (this.callOptionMenuView) {
                    return 'CallOptionMenu';
                }
                if (this.callParticipantCardPopoverContentView) {
                    return 'CallParticipantCardPopoverContentView';
                }
                if (this.channelInvitationForm) {
                    return 'ChannelInvitationForm';
                }
                if (this.emojiPickerView) {
                    return 'EmojiPickerView';
                }
                if (this.activityButtonViewOwnerAsActivityList) {
                    return 'ActivityListView';
                }
                if (this.messageNotificationPopoverContentView) {
                    return 'MessageNotificationPopoverContent';
                }
                return clear();
            },
            default: '',
            required: true,
        }),
        /**
         * If set, the content of this popover view is a list of emojis.
         */
        emojiPickerView: one('EmojiPickerView', {
            compute() {
                if (this.composerViewOwnerAsEmoji) {
                    return {};
                }
                if (this.messageActionViewOwnerAsReaction) {
                    return {};
                }
                return clear();
            },
            inverse: 'popoverViewOwner',
        }),
        manager: one('PopoverManager', {
            compute() {
                if (this.messaging.popoverManager) {
                    return this.messaging.popoverManager;
                }
                return clear();
            },
            inverse: 'popoverViews',
        }),
        /**
         * If set, this popover view is owned by a message action view.
         */
        messageActionViewOwnerAsReaction: one('MessageActionView', {
            identifying: true,
            inverse: 'reactionPopoverView',
        }),
        messageNotificationPopoverContentView: one('MessageNotificationPopoverContentView', {
            compute() {
                if (this.messageViewOwnerAsNotificationContent) {
                    return {};
                }
                return clear();
            },
            inverse: 'popoverViewOwner',
        }),
        messageViewOwnerAsNotificationContent: one('MessageView', {
            identifying: true,
            inverse: 'notificationPopoverView',
        }),
        /**
         * Position of the popover view relative to its anchor point.
         * Valid values: 'top', 'right', 'bottom', 'left'
         */
        position: attr({
            compute() {
                if (this.activityViewOwnerAsMarkDone) {
                    return 'right';
                }
                if (this.callActionListViewOwnerAsMoreMenu) {
                    return 'top';
                }
                if (this.callParticipantCardOwner) {
                    return 'bottom';
                }
                if (this.threadViewTopbarOwnerAsInvite) {
                    return 'bottom';
                }
                if (this.composerViewOwnerAsEmoji) {
                    return 'top';
                }
                if (this.activityButtonViewOwnerAsActivityList) {
                    return 'bottom-start';
                }
                if (this.messageActionViewOwnerAsReaction) {
                    return 'top';
                }
                return clear();
            },
            default: 'top',
        }),
        /**
         * If set, this popover view is owned by a thread view topbar record.
         */
        threadViewTopbarOwnerAsInvite: one('ThreadViewTopbar', {
            identifying: true,
            inverse: 'invitePopoverView',
        }),
    },
});
