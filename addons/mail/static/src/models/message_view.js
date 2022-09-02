/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'MessageView',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * Briefly highlights the message.
         */
        highlight() {
            this.update({
                highlightTimer: { doReset: this.highlightTimer ? true : undefined },
                isHighlighted: true,
            });
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClick(ev) {
            if (ev.target.closest('.o_channel_redirect')) {
                // avoid following dummy href
                ev.preventDefault();
                const channel = this.messaging.models['Thread'].insert({
                    id: Number(ev.target.dataset.oeId),
                    model: 'mail.channel',
                });
                if (!channel.isPinned) {
                    await channel.join();
                    channel.update({ isServerPinned: true });
                }
                channel.open();
                return;
            } else if (ev.target.closest('.o_mail_redirect')) {
                ev.preventDefault();
                this.messaging.openChat({
                    partnerId: Number(ev.target.dataset.oeId)
                });
                return;
            }
            if (ev.target.tagName === 'A') {
                if (ev.target.dataset.oeId && ev.target.dataset.oeModel) {
                    // avoid following dummy href
                    ev.preventDefault();
                    this.messaging.openProfile({
                        id: Number(ev.target.dataset.oeId),
                        model: ev.target.dataset.oeModel,
                    });
                }
                return;
            }
            if (
                !isEventHandled(ev, 'Message.ClickAuthorAvatar') &&
                !isEventHandled(ev, 'Message.ClickAuthorName') &&
                !isEventHandled(ev, 'Message.ClickFailure') &&
                !isEventHandled(ev, 'MessageActionList.Click') &&
                !isEventHandled(ev, 'MessageReactionGroup.Click') &&
                !isEventHandled(ev, 'MessageInReplyToView.ClickMessageInReplyTo') &&
                !isEventHandled(ev, 'PersonaImStatusIcon.Click')
            ) {
                if (this.messagingAsClickedMessageView) {
                    this.messaging.update({ clickedMessageView: clear() });
                } else {
                    this.messaging.update({ clickedMessageView: this });
                }
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickAuthorAvatar(ev) {
            markEventHandled(ev, 'Message.ClickAuthorAvatar');
            if (!this.hasAuthorOpenChat) {
                return;
            }
            this.message.author.openChat();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickAuthorName(ev) {
            markEventHandled(ev, 'Message.ClickAuthorName');
            if (!this.message.author) {
                return;
            }
            this.message.author.openChat();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickFailure(ev) {
            markEventHandled(ev, 'Message.ClickFailure');
            this.message.openResendAction();
        },
        onClickNotificationIcon() {
            this.update({ notificationPopoverView: this.notificationPopoverView ? clear() : {} });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickOriginThread(ev) {
            ev.preventDefault();
            this.message.originThread.open();
        },
        onComponentUpdate() {
            if (!this.exists()) {
                return;
            }
            if (this.doHighlight && this.component && this.component.root.el) {
                this.component.root.el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                this.highlight();
                this.update({ doHighlight: clear() });
            }
            if (this.threadViewOwnerAsLastMessageView && this.component && this.component.isPartiallyVisible()) {
                this.threadViewOwnerAsLastMessageView.handleVisibleMessage(this.message);
            }
        },
        onHighlightTimerTimeout() {
            this.update({
                highlightTimer: clear(),
                isHighlighted: false,
            });
        },
        onMouseenter() {
            if (!this.exists()) {
                return;
            }
            this.update({ isHovered: true });
        },
        onMouseleave() {
            if (!this.exists()) {
                return;
            }
            this.update({
                isHovered: false,
                messagingAsClickedMessageView: clear(),
            });
        },
        /**
         * Action to initiate reply to current messageView.
         */
        replyTo() {
            // When already replying to this messageView, discard the reply.
            if (this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.replyingToMessageView === this) {
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.composerView.discard();
                return;
            }
            this.message.originThread.update({
                composer: {
                    isLog: !this.message.is_discussion && !this.message.is_notification,
                },
            });
            this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.update({
                replyingToMessageView: this,
                composerView: {
                    doFocus: true,
                },
            });
        },
        /**
         * Starts editing this message.
         */
        startEditing() {
            const parser = new DOMParser();
            const htmlDoc = parser.parseFromString(this.message.body.replaceAll('<br>', '\n').replaceAll('</br>', '\n'), "text/html");
            const textInputContent = htmlDoc.body.textContent;
            this.update({
                composerForEditing: {
                    rawMentionedPartners: this.message.recipients,
                    textInputContent,
                    textInputCursorEnd: textInputContent.length,
                    textInputCursorStart: textInputContent.length,
                    textInputSelectionDirection: 'none',
                },
                composerViewInEditing: {
                    doFocus: true,
                    hasToRestoreContent: true,
                },
            });
        },
        /**
         * Stops editing this message.
         */
        stopEditing() {
            if (this.messageListViewItemOwner && this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.composerView && !this.messaging.device.isMobileDevice) {
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.composerView.update({ doFocus: true });
            }
            this.update({
                composerForEditing: clear(),
                composerViewInEditing: clear(),
            });
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeAttachmentList() {
            return (this.message && this.message.attachments.length > 0)
                ? {}
                : clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeAuthorTitleText() {
            return this.hasAuthorOpenChat ? this.env._t("Open chat") : '';
        },
        /**
         * @returns {string}
         */
        _computeDateFromNow() {
            if (!this.message) {
                return clear();
            }
            if (!this.message.date) {
                return clear();
            }
            if (!this.clockWatcher.clock.date) {
                return clear();
            }
            const now = moment(this.clockWatcher.clock.date.getTime());
            if (now.diff(this.message.date, 'seconds') < 45) {
                return this.env._t("now");
            }
            return this.message.date.fromNow();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeExtraClass() {
            if (this.messageListViewItemOwner) {
                return 'o_MessageList_item o_MessageList_message';
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeFailureNotificationIconClassName() {
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeFailureNotificationIconLabel() {
            return clear();
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasAuthorOpenChat() {
            if (this.messaging.currentGuest) {
                return false;
            }
            if (!this.message) {
                return clear();
            }
            if (!this.message.author) {
                return false;
            }
            if (
                this.messageListViewItemOwner &&
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread &&
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread.channel &&
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread.channel.correspondent === this.message.author
            ) {
                return false;
            }
            return true;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsActive() {
            return Boolean(
                this.isHovered ||
                this.messagingAsClickedMessageView ||
                (this.messageActionList && this.messageActionList.actionReaction && this.messageActionList.actionReaction.messageActionView && this.messageActionList.actionReaction.messageActionView.reactionPopoverView) ||
                (this.messageActionList && this.messageActionList.actionDelete && this.messageActionList.actionDelete.messageActionView && this.messageActionList.actionDelete.messageActionView.deleteConfirmDialog)
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsInDiscuss() {
            return Boolean(
                this.messageListViewItemOwner &&
                (
                    this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.threadViewer.discuss ||
                    this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.threadViewer.discussPublicView
                )
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsInChatWindow() {
            return Boolean(
                this.messageListViewItemOwner &&
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.threadViewer.chatWindow
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsInChatter() {
            return Boolean(
                this.messageListViewItemOwner &&
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.threadViewer.chatter
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsInChatWindowAndIsAlignedRight() {
            return Boolean(
                this.isInChatWindow &&
                this.message &&
                this.message.isCurrentUserOrGuestAuthor
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
         _computeIsInChatWindowAndIsAlignedLeft() {
            return Boolean(
                this.isInChatWindow &&
                this.message &&
                !this.message.isCurrentUserOrGuestAuthor
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsShowingAuthorName() {
            return Boolean(
                !(
                    this.isInChatWindow &&
                    (
                        (
                            this.message &&
                            this.message.isCurrentUserOrGuestAuthor
                        ) ||
                        (
                            this.messageListViewItemOwner &&
                            this.messageListViewItemOwner.messageListViewOwner.thread.channel &&
                            this.messageListViewItemOwner.messageListViewOwner.thread.channel.channel_type === 'chat'
                        )
                    )
                )
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsSelected() {
            return Boolean(
                this.messageListViewItemOwner &&
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.replyingToMessageView === this
            );
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeIsSquashed() {
            if (this.messageListViewItemOwner) {
                return this.messageListViewItemOwner.isSquashed;
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessage() {
            if (this.messageListViewItemOwner) {
                return this.messageListViewItemOwner.message;
            }
            if (this.deleteMessageConfirmViewOwner) {
                return this.deleteMessageConfirmViewOwner.message;
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessageActionList() {
            return this.deleteMessageConfirmViewOwner ? clear() : {};
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMessageInReplyToView() {
            return (
                this.message &&
                this.message.originThread &&
                this.message.originThread.model === 'mail.channel' &&
                this.message.parentMessage
            ) ? {} : clear();
        },
        /**
         * @private
         * @retuns {FieldCommand}
         */
        _computeMessageSeenIndicatorView() {
            if (
                this.message.isCurrentUserOrGuestAuthor &&
                this.messageListViewItemOwner &&
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread &&
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread.hasSeenIndicators
            ) {
                return {};
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeNotificationIconClassName() {
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeNotificationIconLabel() {
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computePersonaImStatusIconView() {
            if (this.message.guestAuthor && this.message.guestAuthor.im_status) {
                return {};
            }
            return this.message.author && this.message.author.isImStatusSet ? {} : clear();
        },
    },
    fields: {
        /**
         * Determines the attachment list displaying the attachments of this
         * message (if any).
         */
        attachmentList: one('AttachmentList', {
            compute: '_computeAttachmentList',
            inverse: 'messageViewOwner',
            isCausal: true,
        }),
        authorTitleText: attr({
            compute: '_computeAuthorTitleText',
        }),
        clockWatcher: one('ClockWatcher', {
            default: {
                clock: {
                    frequency: 60 * 1000,
                },
            },
            inverse: 'messageViewOwner',
            isCausal: true,
        }),
        /**
         * States the component displaying this message view (if any).
         */
        component: attr(),
        composerForEditing: one('Composer', {
            inverse: 'messageViewInEditing',
            isCausal: true,
        }),
        /**
        * Determines the composer that is used to edit this message (if any).
        */
        composerViewInEditing: one('ComposerView', {
            inverse: 'messageViewInEditing',
            isCausal: true,
        }),
        /**
         * States the time elapsed since date up to now.
         */
        dateFromNow: attr({
            compute: '_computeDateFromNow',
        }),
        /**
         * States the delete message confirm view that is displaying this
         * message view.
         */
        deleteMessageConfirmViewOwner: one('DeleteMessageConfirmView', {
            identifying: true,
            inverse: 'messageView',
        }),
        /**
         * Determines whether this message view should be highlighted at next
         * render. Scrolls into view and briefly highlights it.
         */
        doHighlight: attr(),
        /**
         * Determines which extra class this message view component should have.
         */
        extraClass: attr({
            compute: '_computeExtraClass',
            default: '',
        }),
        failureNotificationIconClassName: attr({
            compute: '_computeFailureNotificationIconClassName',
            default: 'fa fa-envelope',
        }),
        failureNotificationIconLabel: attr({
            compute: '_computeFailureNotificationIconLabel',
            default: '',
        }),
        /**
         * Determines whether author open chat feature is enabled on message.
         */
        hasAuthorOpenChat: attr({
            compute: '_computeHasAuthorOpenChat',
        }),
        /**
         * Current timer that will reset isHighlighted to false.
         */
        highlightTimer: one('Timer', {
            inverse: 'messageViewOwnerAsHighlight',
            isCausal: true,
        }),
        /**
         * Whether the message is "active", ie: hovered or clicked, and should
         * display additional things (date in sidebar, message actions, etc.)
         */
        isActive: attr({
            compute: '_computeIsActive',
        }),
        /**
         * Whether the message should be forced to be isHighlighted. Should only
         * be set through @see highlight()
         */
        isHighlighted: attr(),
        /**
         * Determine whether the message is hovered. When message is hovered
         * it displays message actions.
         */
        isHovered: attr({
            default: false,
        }),
        /**
         * Determines if we are in the Discuss view.
         */
        isInDiscuss: attr({
            compute: '_computeIsInDiscuss',
        }),
        /**
         * Determines if we are in the ChatWindow view.
         */
        isInChatWindow: attr({
            compute: '_computeIsInChatWindow',
        }),
        /**
         * Determines if we are in the Chatter view.
         */
        isInChatter: attr({
            compute: '_computeIsInChatter',
        }),
        /**
         * Determines if we are in the ChatWindow view AND if the message is right aligned
         */
        isInChatWindowAndIsAlignedRight: attr({
            compute: '_computeIsInChatWindowAndIsAlignedRight',
        }),
        /**
         * Determines if we are in the ChatWindow view AND if the message is left aligned
         */
        isInChatWindowAndIsAlignedLeft: attr({
            compute: '_computeIsInChatWindowAndIsAlignedLeft',
        }),
        /**
         * Determines if the author name is displayed.
         */
        isShowingAuthorName: attr({
            compute: '_computeIsShowingAuthorName',
        }),
        /**
         * Tells whether the message is selected in the current thread viewer.
         */
        isSelected: attr({
            compute: '_computeIsSelected',
            default: false,
        }),
        /**
         * Determines whether this message view should be squashed visually.
         */
        isSquashed: attr({
            compute: '_computeIsSquashed',
            default: false,
        }),
        /**
         * Determines the message action list of this message view (if any).
         */
        messageActionList: one('MessageActionList', {
            compute: '_computeMessageActionList',
            inverse: 'messageView',
            isCausal: true,
        }),
        /**
         * Determines the message that is displayed by this message view.
         */
        message: one('Message', {
            compute: '_computeMessage',
            inverse: 'messageViews',
            required: true,
        }),
        /**
         * States the message in reply to view that displays the message of
         * which this message is a reply to (if any).
         */
        messageInReplyToView: one('MessageInReplyToView', {
            compute: '_computeMessageInReplyToView',
            inverse: 'messageView',
            isCausal: true,
        }),
        messageListViewItemOwner: one('MessageListViewItem', {
            identifying: true,
            inverse: 'messageView',
        }),
        messageSeenIndicatorView: one('MessageSeenIndicatorView', {
            compute: '_computeMessageSeenIndicatorView',
            inverse: 'messageViewOwner',
            isCausal: true,
        }),
        messagingAsClickedMessageView: one('Messaging', {
            inverse: 'clickedMessageView',
        }),
        notificationIconClassName: attr({
            compute: '_computeNotificationIconClassName',
            default: 'fa fa-envelope-o',
        }),
        notificationIconLabel: attr({
            compute: '_computeNotificationIconLabel',
            default: '',
        }),
        notificationIconRef: attr(),
        notificationPopoverView: one('PopoverView', {
            inverse: 'messageViewOwnerAsNotificationContent',
            isCausal: true,
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute: '_computePersonaImStatusIconView',
            inverse: 'messageViewOwner',
            isCausal: true,
        }),
        /**
         * States whether this message view is the last one of its thread view.
         * Computed from inverse relation.
         */
        threadViewOwnerAsLastMessageView: one('ThreadView', {
            inverse: 'lastMessageView',
            readonly: true,
        }),
    },
});
