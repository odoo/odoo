/** @odoo-module **/

import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
import { attr, clear, one, Model } from "@mail/model";

import { usePosition } from "@web/core/position_hook";

Model({
    name: "PopoverView",
    template: "mail.PopoverView",
    componentSetup() {
        useComponentToModel({ fieldName: "component" });
        usePosition(() => this.anchorRef && this.anchorRef.el, {
            popper: "root",
            margin: 16,
            position: this.position,
        });
    },
    identifyingMode: "xor",
    lifecycleHooks: {
        _created() {
            document.addEventListener("click", this._onClickCaptureGlobal, true);
        },
        _willDelete() {
            document.removeEventListener("click", this._onClickCaptureGlobal, true);
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
            return Boolean(
                this.component && this.component.root.el && this.component.root.el.contains(element)
            );
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
        activityButtonViewOwnerAsActivityList: one("ActivityButtonView", {
            identifying: true,
            inverse: "activityListPopoverView",
        }),
        activityCellViewOwnerAsActivityList: one("ActivityCellView", {
            identifying: true,
            inverse: "activityListPopoverView",
        }),
        activityListView: one("ActivityListView", {
            inverse: "popoverViewOwner",
            compute() {
                return this.activityButtonViewOwnerAsActivityList ||
                    this.activityCellViewOwnerAsActivityList
                    ? {}
                    : clear();
            },
        }),
        activityMarkDonePopoverContentView: one("ActivityMarkDonePopoverContentView", {
            inverse: "popoverViewOwner",
            compute() {
                if (this.activityViewOwnerAsMarkDone) {
                    return {};
                }
                return clear();
            },
        }),
        activityViewOwnerAsMarkDone: one("ActivityView", {
            identifying: true,
            inverse: "markDonePopoverView",
        }),
        /**
         * HTML element that is used as anchor position for this popover view.
         */
        anchorRef: attr({
            required: true,
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
                if (this.activityCellViewOwnerAsActivityList) {
                    return this.activityCellViewOwnerAsActivityList.contentRef;
                }
                if (this.messageActionViewOwnerAsReaction) {
                    return this.messageActionViewOwnerAsReaction.actionRef;
                }
                if (this.messageViewOwnerAsNotificationContent) {
                    return this.messageViewOwnerAsNotificationContent.notificationIconRef;
                }
                return clear();
            },
        }),
        callActionListViewOwnerAsMoreMenu: one("CallActionListView", {
            identifying: true,
            inverse: "moreMenuPopoverView",
        }),
        callOptionMenuView: one("CallOptionMenu", {
            inverse: "popoverViewOwner",
            compute() {
                if (this.callActionListViewOwnerAsMoreMenu) {
                    return {};
                }
                return clear();
            },
        }),
        callParticipantCardOwner: one("CallParticipantCard", {
            identifying: true,
            inverse: "callParticipantCardPopoverView",
        }),
        callParticipantCardPopoverContentView: one("CallParticipantCardPopoverContentView", {
            inverse: "popoverViewOwner",
            compute() {
                if (this.callParticipantCardOwner) {
                    return {};
                }
                return clear();
            },
        }),
        /**
         * The record that represents the content inside the popover view.
         */
        channelInvitationForm: one("ChannelInvitationForm", {
            inverse: "popoverViewOwner",
            compute() {
                if (this.threadViewTopbarOwnerAsInvite) {
                    return {};
                }
                return clear();
            },
        }),
        /**
         * States the OWL component of this popover view.
         */
        component: attr(),
        /**
         * If set, this popover view is owned by a composer view.
         */
        composerViewOwnerAsEmoji: one("ComposerView", {
            identifying: true,
            inverse: "emojisPopoverView",
        }),
        /**
         * Determines the record that is content of this popover view.
         */
        content: one("Record", {
            required: true,
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
                if (
                    this.activityButtonViewOwnerAsActivityList ||
                    this.activityCellViewOwnerAsActivityList
                ) {
                    return this.activityListView;
                }
                if (this.messageNotificationPopoverContentView) {
                    return this.messageNotificationPopoverContentView;
                }
                return clear();
            },
        }),
        /**
         * Determines the class name for the component
         * that is content of this popover view.
         */
        contentClassName: attr({
            default: "",
            compute() {
                if (this.channelInvitationForm) {
                    return "o_PopoverView_channelInvitationForm";
                }
                if (this.emojiPickerView) {
                    return "o_PopoverView_emojiPickerView";
                }
                return clear();
            },
        }),
        /**
         * Determines the component name of the content.
         */
        contentComponentName: attr({
            default: "",
            required: true,
            compute() {
                if (this.activityMarkDonePopoverContentView) {
                    return "ActivityMarkDonePopoverContentView";
                }
                if (this.callOptionMenuView) {
                    return "CallOptionMenu";
                }
                if (this.callParticipantCardPopoverContentView) {
                    return "CallParticipantCardPopoverContentView";
                }
                if (this.channelInvitationForm) {
                    return "ChannelInvitationForm";
                }
                if (this.emojiPickerView) {
                    return "EmojiPickerView";
                }
                if (
                    this.activityButtonViewOwnerAsActivityList ||
                    this.activityCellViewOwnerAsActivityList
                ) {
                    return "ActivityListView";
                }
                if (this.messageNotificationPopoverContentView) {
                    return "MessageNotificationPopoverContentView";
                }
                return clear();
            },
        }),
        /**
         * If set, the content of this popover view is a list of emojis.
         */
        emojiPickerView: one("EmojiPickerView", {
            inverse: "popoverViewOwner",
            compute() {
                if (this.composerViewOwnerAsEmoji || this.messageActionViewOwnerAsReaction) {
                    return {};
                }
                return clear();
            },
        }),
        manager: one("PopoverManager", {
            inverse: "popoverViews",
            compute() {
                if (this.messaging.popoverManager) {
                    return this.messaging.popoverManager;
                }
                return clear();
            },
        }),
        /**
         * If set, this popover view is owned by a message action view.
         */
        messageActionViewOwnerAsReaction: one("MessageActionView", {
            identifying: true,
            inverse: "reactionPopoverView",
        }),
        messageNotificationPopoverContentView: one("MessageNotificationPopoverContentView", {
            inverse: "popoverViewOwner",
            compute() {
                if (this.messageViewOwnerAsNotificationContent) {
                    return {};
                }
                return clear();
            },
        }),
        messageViewOwnerAsNotificationContent: one("MessageView", {
            identifying: true,
            inverse: "notificationPopoverView",
        }),
        /**
         * Position of the popover view relative to its anchor point.
         * Valid values: 'top', 'right', 'bottom', 'left'
         */
        position: attr({
            default: "top",
            compute() {
                if (this.activityViewOwnerAsMarkDone) {
                    return "right";
                }
                if (this.callActionListViewOwnerAsMoreMenu) {
                    return "top";
                }
                if (this.callParticipantCardOwner) {
                    return "bottom";
                }
                if (this.threadViewTopbarOwnerAsInvite) {
                    return "bottom";
                }
                if (this.composerViewOwnerAsEmoji) {
                    return "top";
                }
                if (this.activityButtonViewOwnerAsActivityList) {
                    return "bottom-start";
                }
                if (this.activityCellViewOwnerAsActivityList) {
                    return "bottom-start";
                }
                if (this.messageActionViewOwnerAsReaction) {
                    return "top";
                }
                return clear();
            },
        }),
        /**
         * If set, this popover view is owned by a thread view topbar record.
         */
        threadViewTopbarOwnerAsInvite: one("ThreadViewTopbar", {
            identifying: true,
            inverse: "invitePopoverView",
        }),
    },
});
