/** @odoo-module **/

import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
import { useUpdateToModel } from "@mail/component_hooks/use_update_to_model";
import { attr, clear, increment, one, Model } from "@mail/model";
import { isEventHandled, markEventHandled } from "@mail/utils/utils";

Model({
    name: "MessageView",
    template: "mail.MessageView",
    componentSetup() {
        useComponentToModel({ fieldName: "component" });
        useUpdateToModel({ methodName: "onComponentUpdate" });
    },
    identifyingMode: "xor",
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
            if (ev.target.closest(".o_channel_redirect")) {
                // avoid following dummy href
                ev.preventDefault();
                const channel = this.messaging.models["Thread"].insert({
                    id: Number(ev.target.dataset.oeId),
                    model: "mail.channel",
                });
                if (!channel.isPinned) {
                    await channel.join();
                    channel.update({ isServerPinned: true });
                }
                channel.open();
                return;
            } else if (ev.target.closest(".o_mail_redirect")) {
                ev.preventDefault();
                this.messaging.openChat({
                    partnerId: Number(ev.target.dataset.oeId),
                });
                return;
            }
            if (ev.target.tagName === "A") {
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
                !isEventHandled(ev, "Message.ClickAuthorAvatar") &&
                !isEventHandled(ev, "Message.ClickAuthorName") &&
                !isEventHandled(ev, "Message.ClickFailure") &&
                !isEventHandled(ev, "MessageActionList.Click") &&
                !isEventHandled(ev, "MessageReactionGroup.Click") &&
                !isEventHandled(ev, "MessageInReplyToView.ClickMessageInReplyTo") &&
                !isEventHandled(ev, "PersonaImStatusIcon.Click")
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
            markEventHandled(ev, "Message.ClickAuthorAvatar");
            if (!this.message.author || !this.hasAuthorClickable) {
                return;
            }
            if (!this.hasAuthorOpenChat) {
                this.message.author.openProfile();
                return;
            }
            this.message.author.openChat();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickAuthorName(ev) {
            markEventHandled(ev, "Message.ClickAuthorName");
            if (!this.message.author || !this.hasAuthorClickable) {
                return;
            }
            if (!this.hasAuthorOpenChat) {
                this.message.author.openProfile();
                return;
            }
            this.message.author.openChat();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickFailure(ev) {
            markEventHandled(ev, "Message.ClickFailure");
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
                this.component.root.el.scrollIntoView({ behavior: "smooth", block: "center" });
                this.highlight();
                this.update({ doHighlight: clear() });
            }
            if (
                this.messageListViewItemOwner &&
                this.messageListViewItemOwner.threadViewOwnerAsLastMessageListViewItem &&
                this.messageListViewItemOwner.isPartiallyVisible()
            ) {
                this.messageListViewItemOwner.threadViewOwnerAsLastMessageListViewItem.handleVisibleMessage(
                    this.message
                );
            }
            if (
                this.prettyBodyRef.el &&
                (this.message.prettyBody !== this.lastPrettyBody ||
                    (this.message.prettyBody && this.prettyBodyRef.el.innerHTML === ""))
            ) {
                this.prettyBodyRef.el.innerHTML = this.message.prettyBody;
                this.update({ lastPrettyBody: this.message.prettyBody });
            }
            if (!this.prettyBodyRef.el) {
                this.update({ lastPrettyBody: clear() });
            }
            // Remove all readmore before if any before reinsert them with insertReadMoreLess.
            // This is needed because insertReadMoreLess is working with direct DOM mutations
            // which are not sync with Owl.
            if (this.contentRef.el) {
                for (const el of this.contentRef.el.querySelectorAll(
                    ":scope .o_MessageView_readMoreLess"
                )) {
                    el.remove();
                }
                this.update({ lastReadMoreIndex: clear() });
                this.insertReadMoreLess($(this.contentRef.el));
                this.messaging.messagingBus.trigger("o-component-message-read-more-less-inserted", {
                    message: this.message,
                });
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
         * Modifies the message to add the 'read more/read less' functionality
         * All element nodes with 'data-o-mail-quote' attribute are concerned.
         * All text nodes after a ``#stopSpelling`` element are concerned.
         * Those text nodes need to be wrapped in a span (toggle functionality).
         * All consecutive elements are joined in one 'read more/read less'.
         *
         * FIXME This method should be rewritten (task-2308951)
         *
         * @param {jQuery} $element
         */
        insertReadMoreLess($element) {
            const groups = [];
            let readMoreNodes;

            // nodeType 1: element_node
            // nodeType 3: text_node
            const $children = $element
                .contents()
                .filter(
                    (index, content) =>
                        content.nodeType === 1 ||
                        (content.nodeType === 3 && content.nodeValue.trim())
                );

            for (const child of $children) {
                let $child = $(child);

                // Hide Text nodes if "stopSpelling"
                if (child.nodeType === 3 && $child.prevAll('[id*="stopSpelling"]').length > 0) {
                    // Convert Text nodes to Element nodes
                    $child = $("<span>", {
                        text: child.textContent,
                        "data-o-mail-quote": "1",
                    });
                    child.parentNode.replaceChild($child[0], child);
                }

                // Create array for each 'read more' with nodes to toggle
                if (
                    $child.attr("data-o-mail-quote") ||
                    ($child.get(0).nodeName === "BR" &&
                        $child.prev('[data-o-mail-quote="1"]').length > 0)
                ) {
                    if (!readMoreNodes) {
                        readMoreNodes = [];
                        groups.push(readMoreNodes);
                    }
                    $child.hide();
                    readMoreNodes.push($child);
                } else {
                    readMoreNodes = undefined;
                    this.insertReadMoreLess($child);
                }
            }

            for (const group of groups) {
                const index = this.update({ lastReadMoreIndex: increment() });
                // Insert link just before the first node
                const $readMoreLess = $("<a>", {
                    class: "o_MessageView_readMoreLess d-block",
                    href: "#",
                    text: this.readMoreText,
                }).insertBefore(group[0]);

                // Toggle All next nodes
                if (!this.isReadMoreByIndex.has(index)) {
                    this.isReadMoreByIndex.set(index, true);
                }
                const updateFromState = () => {
                    const isReadMore = this.isReadMoreByIndex.get(index);
                    for (const $child of group) {
                        $child.hide();
                        $child.toggle(!isReadMore);
                    }
                    $readMoreLess.text(isReadMore ? this.readMoreText : this.readLessText);
                };
                $readMoreLess.click((e) => {
                    e.preventDefault();
                    this.isReadMoreByIndex.set(index, !this.isReadMoreByIndex.get(index));
                    updateFromState();
                });
                updateFromState();
            }
        },
        /**
         * Action to initiate reply to current messageView.
         */
        replyTo() {
            // When already replying to this messageView, discard the reply.
            if (
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner
                    .replyingToMessageView === this
            ) {
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.composerView.discard();
                return;
            }
            this.message.originThread.update({
                composer: {
                    isLog:
                        !this.message.is_discussion &&
                        this.message.message_type !== "user_notification",
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
            const htmlDoc = parser.parseFromString(
                this.message.body.replaceAll("<br>", "\n").replaceAll("</br>", "\n"),
                "text/html"
            );
            const textInputContent = htmlDoc.body.textContent;
            this.update({
                composerForEditing: {
                    rawMentionedPartners: this.message.recipients,
                    textInputContent,
                    textInputCursorEnd: textInputContent.length,
                    textInputCursorStart: textInputContent.length,
                    textInputSelectionDirection: "none",
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
            if (
                this.messageListViewItemOwner &&
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.composerView &&
                !this.messaging.device.isMobileDevice
            ) {
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.composerView.update(
                    { doFocus: true }
                );
            }
            this.update({
                composerForEditing: clear(),
                composerViewInEditing: clear(),
            });
        },
    },
    fields: {
        /**
         * Determines the attachment list displaying the attachments of this
         * message (if any).
         */
        attachmentList: one("AttachmentList", {
            inverse: "messageViewOwner",
            compute() {
                return this.message && this.message.attachments.length > 0 ? {} : clear();
            },
        }),
        authorTitleText: attr({
            compute() {
                return this.hasAuthorOpenChat
                    ? this.env._t("Open chat")
                    : this.hasAuthorClickable
                    ? this.env._t("Open profile")
                    : "";
            },
        }),
        clockWatcher: one("ClockWatcher", {
            default: { clock: { frequency: 60 * 1000 } },
            inverse: "messageViewOwner",
        }),
        /**
         * States the component displaying this message view (if any).
         */
        component: attr(),
        composerForEditing: one("Composer", { inverse: "messageViewInEditing" }),
        /**
         * Determines the composer that is used to edit this message (if any).
         */
        composerViewInEditing: one("ComposerView", { inverse: "messageViewInEditing" }),
        /**
         * Reference to the content of the message.
         */
        contentRef: attr({ ref: "content" }),
        /**
         * States the time elapsed since date up to now.
         */
        dateFromNow: attr({
            compute() {
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
                if (now.diff(this.message.momentDate, "seconds") < 45) {
                    return this.env._t("now");
                }
                return this.message.momentDate.fromNow();
            },
        }),
        /**
         * States the delete message confirm view that is displaying this
         * message view.
         */
        deleteMessageConfirmViewOwner: one("DeleteMessageConfirmView", {
            identifying: true,
            inverse: "messageView",
        }),
        /**
         * Determines whether this message view should be highlighted at next
         * render. Scrolls into view and briefly highlights it.
         */
        doHighlight: attr(),
        failureNotificationIconClassName: attr({
            default: "fa fa-envelope",
            compute() {
                return clear();
            },
        }),
        failureNotificationIconLabel: attr({
            default: "",
            compute() {
                return clear();
            },
        }),
        /**
         * Determines whether author open chat feature is enabled on message.
         */
        hasAuthorOpenChat: attr({
            compute() {
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
                    this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread
                        .channel &&
                    this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread
                        .channel.correspondent === this.message.author
                ) {
                    return false;
                }
                return true;
            },
        }),
        hasAuthorClickable: attr({
            compute() {
                return this.hasAuthorOpenChat;
            },
        }),
        /**
         * Current timer that will reset isHighlighted to false.
         */
        highlightTimer: one("Timer", { inverse: "messageViewOwnerAsHighlight" }),
        /**
         * Whether the message is "active", ie: hovered or clicked, and should
         * display additional things (date in sidebar, message actions, etc.)
         */
        isActive: attr({
            compute() {
                return Boolean(
                    this.isHovered ||
                        this.messagingAsClickedMessageView ||
                        (this.messageActionList &&
                            this.messageActionList.actionReaction &&
                            this.messageActionList.actionReaction.messageActionView &&
                            this.messageActionList.actionReaction.messageActionView
                                .reactionPopoverView) ||
                        (this.messageActionList &&
                            this.messageActionList.actionDelete &&
                            this.messageActionList.actionDelete.messageActionView &&
                            this.messageActionList.actionDelete.messageActionView
                                .deleteConfirmDialog)
                );
            },
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
        isHovered: attr({ default: false }),
        /**
         * Determines if we are in the Discuss view.
         */
        isInDiscuss: attr({
            compute() {
                return Boolean(
                    this.messageListViewItemOwner &&
                        (this.messageListViewItemOwner.messageListViewOwner.threadViewOwner
                            .threadViewer.discuss ||
                            this.messageListViewItemOwner.messageListViewOwner.threadViewOwner
                                .threadViewer.discussPublicView)
                );
            },
        }),
        /**
         * Determines if we are in the ChatWindow view.
         */
        isInChatWindow: attr({
            compute() {
                return Boolean(
                    this.messageListViewItemOwner &&
                        this.messageListViewItemOwner.messageListViewOwner.threadViewOwner
                            .threadViewer.chatWindow
                );
            },
        }),
        /**
         * Determines if we are in the Chatter view.
         */
        isInChatter: attr({
            compute() {
                return Boolean(
                    this.messageListViewItemOwner &&
                        this.messageListViewItemOwner.messageListViewOwner.threadViewOwner
                            .threadViewer.chatter
                );
            },
        }),
        /**
         * Determines if we are in the ChatWindow view AND if the message is right aligned
         */
        isInChatWindowAndIsAlignedRight: attr({
            compute() {
                return Boolean(
                    this.isInChatWindow && this.message && this.message.isCurrentUserOrGuestAuthor
                );
            },
        }),
        /**
         * Determines if we are in the ChatWindow view AND if the message is left aligned
         */
        isInChatWindowAndIsAlignedLeft: attr({
            compute() {
                return Boolean(
                    this.isInChatWindow && this.message && !this.message.isCurrentUserOrGuestAuthor
                );
            },
        }),
        /**
         * Determines whether each "read more" is opened or closed. The keys are
         * index, which is determined by their order of appearance in the DOM.
         * If body changes so that "read more" count is different, their default
         * value will be "wrong" at the next render but this is an acceptable
         * limitation. It's more important to save the state correctly in a
         * typical non-changing situation.
         */
        isReadMoreByIndex: attr({
            compute() {
                return new Map();
            },
        }),
        /**
         * Determines if the author name is displayed.
         */
        isShowingAuthorName: attr({
            compute() {
                return Boolean(
                    !(
                        this.isInChatWindow &&
                        ((this.message && this.message.isCurrentUserOrGuestAuthor) ||
                            (this.messageListViewItemOwner &&
                                this.messageListViewItemOwner.messageListViewOwner.thread.channel &&
                                this.messageListViewItemOwner.messageListViewOwner.thread.channel
                                    .channel_type === "chat"))
                    )
                );
            },
        }),
        /**
         * Tells whether the message is selected in the current thread viewer.
         */
        isSelected: attr({
            default: false,
            compute() {
                return Boolean(
                    this.messageListViewItemOwner &&
                        this.messageListViewItemOwner.messageListViewOwner.threadViewOwner
                            .replyingToMessageView === this
                );
            },
        }),
        /**
         * Determines whether this message view should be squashed visually.
         */
        isSquashed: attr({
            default: false,
            compute() {
                if (this.messageListViewItemOwner) {
                    return this.messageListViewItemOwner.isSquashed;
                }
                return clear();
            },
        }),
        /**
         * Value of the last rendered prettyBody. Useful to compare to new value
         * to decide if it has to be updated.
         */
        lastPrettyBody: attr(),
        /**
         * States the index of the last "read more" that was inserted.
         * Useful to remember the state for each "read more" even if their DOM
         * is re-rendered.
         */
        lastReadMoreIndex: attr({ default: 0 }),
        linkPreviewListView: one("LinkPreviewListView", {
            inverse: "messageViewOwner",
            compute() {
                return this.message && this.message.linkPreviews.length > 0 ? {} : clear();
            },
        }),
        /**
         * Determines the message action list of this message view (if any).
         */
        messageActionList: one("MessageActionList", {
            inverse: "messageView",
            compute() {
                return this.deleteMessageConfirmViewOwner ? clear() : {};
            },
        }),
        /**
         * Determines the message that is displayed by this message view.
         */
        message: one("Message", {
            inverse: "messageViews",
            required: true,
            compute() {
                if (this.messageListViewItemOwner) {
                    return this.messageListViewItemOwner.message;
                }
                if (this.deleteMessageConfirmViewOwner) {
                    return this.deleteMessageConfirmViewOwner.message;
                }
                return clear();
            },
        }),
        /**
         * States the message in reply to view that displays the message of
         * which this message is a reply to (if any).
         */
        messageInReplyToView: one("MessageInReplyToView", {
            inverse: "messageView",
            compute() {
                return this.message &&
                    this.message.originThread &&
                    this.message.originThread.model === "mail.channel" &&
                    this.message.parentMessage
                    ? {}
                    : clear();
            },
        }),
        messageListViewItemOwner: one("MessageListViewItem", {
            identifying: true,
            inverse: "messageView",
        }),
        messageSeenIndicatorView: one("MessageSeenIndicatorView", {
            inverse: "messageViewOwner",
            compute() {
                if (
                    this.message.isCurrentUserOrGuestAuthor &&
                    this.messageListViewItemOwner &&
                    this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread &&
                    this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.thread
                        .hasSeenIndicators
                ) {
                    return {};
                }
                return clear();
            },
        }),
        messagingAsClickedMessageView: one("Messaging", { inverse: "clickedMessageView" }),
        notificationIconClassName: attr({
            default: "fa fa-envelope-o",
            compute() {
                return clear();
            },
        }),
        notificationIconLabel: attr({
            default: "",
            compute() {
                return clear();
            },
        }),
        notificationIconRef: attr({ ref: "notificationIcon" }),
        notificationPopoverView: one("PopoverView", {
            inverse: "messageViewOwnerAsNotificationContent",
        }),
        personaImStatusIconView: one("PersonaImStatusIconView", {
            inverse: "messageViewOwner",
            compute() {
                if (this.message.guestAuthor && this.message.guestAuthor.im_status) {
                    return {};
                }
                return this.message.author && this.message.author.isImStatusSet ? {} : clear();
            },
        }),
        /**
         * Reference to element containing the prettyBody. Useful to be able to
         * replace prettyBody with new value in JS (which is faster than t-raw).
         */
        prettyBodyRef: attr({ ref: "prettyBody" }),
        readLessText: attr({
            compute() {
                return this.env._t("Read Less");
            },
        }),
        readMoreText: attr({
            compute() {
                return this.env._t("Read More");
            },
        }),
        /**
         * Scheduled for sending
         */
        scheduledFromNow: attr({
            compute() {
                if (!this.message) {
                    return clear();
                }
                if (!this.message.scheduledMomentDate) {
                    return clear();
                }
                if (!this.clockWatcher.clock.date) {
                    return clear();
                }
                return this.message.scheduledMomentDate.fromNow();
            },
        }),
    },
});
