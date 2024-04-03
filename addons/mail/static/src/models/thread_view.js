/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'ThreadView',
    lifecycleHooks: {
        _willDelete() {
            this.messaging.browser.clearTimeout(this.loaderTimeout);
        },
    },
    recordMethods: {
        /**
         * This function register a hint for the component related to this
         * record. Hints are information on changes around this viewer that
         * make require adjustment on the component. For instance, if this
         * ThreadView initiated a thread cache load and it now has become
         * loaded, then it may need to auto-scroll to last message.
         *
         * @param {string} hintType name of the hint. Used to determine what's
         *   the broad type of adjustement the component has to do.
         * @param {any} [hintData] data of the hint. Used to fine-tune
         *   adjustments on the component.
         */
        addComponentHint(hintType, hintData) {
            const hint = { data: hintData, type: hintType };
            this.update({
                componentHintList: this.componentHintList.concat([hint]),
            });
        },
        /**
         * @param {Message} message
         */
        handleVisibleMessage(message) {
            if (!this.lastVisibleMessage || this.lastVisibleMessage.id < message.id) {
                this.update({ lastVisibleMessage: message });
            }
        },
        /**
         * @param {Object} hint
         */
        markComponentHintProcessed(hint) {
            this.update({
                componentHintList: this.componentHintList.filter(h => h !== hint),
            });
            this.messaging.messagingBus.trigger('o-thread-view-hint-processed', {
                hint,
                threadViewer: this.threadViewer,
            });
        },
        onClickRetryLoadMessages() {
            if (!this.exists()) {
                return;
            }
            if (!this.threadCache) {
                return;
            }
            this.threadCache.update({ hasLoadingFailed: false });
        },
        /**
         * Called when an element in the thread becomes focused.
         */
        onFocusin() {
            if (!this.exists()) {
                // prevent crash on destroy
                return;
            }
            if (this.threadViewer.chatWindow) {
                this.threadViewer.chatWindow.update({ isFocused: true });
            }
        },
        /**
         * Starts editing the last message of this thread from the current user.
         */
        startEditingLastMessageFromCurrentUser() {
            const messageListViewItems = this.messageListView.messageListViewItems;
            messageListViewItems.reverse();
            const messageListViewItem = messageListViewItems.find(messageListViewItem => messageListViewItem.message.isCurrentUserOrGuestAuthor && messageListViewItem.message.canBeDeleted);
            if (messageListViewItem) {
                messageListViewItem.messageView.startEditing();
            }
        },
        /**
         * Not a real field, used to trigger `thread.markAsSeen` when one of
         * the dependencies changes.
         *
         * @private
         * @returns {boolean}
         */
        _computeThreadShouldBeSetAsSeen() {
            if (!this.thread) {
                return;
            }
            if (!this.thread.lastNonTransientMessage) {
                return;
            }
            if (!this.lastVisibleMessage) {
                return;
            }
            if (this.lastVisibleMessage !== this.lastMessage) {
                return;
            }
            if (!this.isComposerFocused) {
                // FIXME condition should not be on "composer is focused" but "threadView is active"
                // See task-2277543
                return;
            }
            if (this.messaging.currentGuest) {
                return;
            }
            this.thread.markAsSeen(this.thread.lastNonTransientMessage);
        },
        /**
         * @private
         */
        _onThreadCacheChanged() {
            if (this.threadCache) {
                // clear obsolete hints
                this.update({ componentHintList: clear() });
                this.addComponentHint('change-of-thread-cache');
                this.threadCache.update({
                    isCacheRefreshRequested: true,
                });
                this.update({ lastVisibleMessage: clear() });
            }
        },
        /**
         * @private
         */
        _onThreadCacheIsLoadingChanged() {
            if (this.threadCache && this.threadCache.isLoading) {
                if (!this.isLoading && !this.isPreparingLoading) {
                    this.update({ isPreparingLoading: true });
                    (new Promise(resolve => {
                            this.update({ loaderTimeout: this.messaging.browser.setTimeout(resolve, this.messaging.loadingBaseDelayDuration) });
                        }
                    )).then(() => {
                        if (!this.exists()) {
                            return;
                        }
                        const isLoading = this.threadCache
                            ? this.threadCache.isLoading
                            : false;
                        this.update({ isLoading, isPreparingLoading: false });
                    });
                }
                return;
            }
            this.messaging.browser.clearTimeout(this.loaderTimeout);
            if (this.thread) {
                this.update({ isLoading: false, isPreparingLoading: false });
            }
        },
        /**
         * @param {Message} prevMessage
         * @param {Message} message
         * @returns {boolean}
         */
        _shouldMessageBeSquashed(prevMessage, message) {
            if (!this.hasSquashCloseMessages) {
                return false;
            }
            if (message.parentMessage) {
                return false;
            }
            if (!prevMessage) {
                return false;
            }
            if (!prevMessage.date && message.date) {
                return false;
            }
            if (message.date && prevMessage.date && Math.abs(message.date.diff(prevMessage.date)) > 60000) {
                // more than 1 min. elasped
                return false;
            }
            if (prevMessage.dateDay !== message.dateDay) {
                return false;
            }
            if (prevMessage.message_type !== 'comment' || message.message_type !== 'comment') {
                return false;
            }
            if (prevMessage.author !== message.author || prevMessage.guestAuthor !== message.guestAuthor) {
                // from a different author
                return false;
            }
            if (prevMessage.originThread !== message.originThread) {
                return false;
            }
            if (
                prevMessage.notifications.length > 0 ||
                message.notifications.length > 0
            ) {
                // visual about notifications is restricted to non-squashed messages
                return false;
            }
            const prevOriginThread = prevMessage.originThread;
            const originThread = message.originThread;
            if (
                prevOriginThread &&
                originThread &&
                prevOriginThread.model === originThread.model &&
                originThread.model !== 'mail.channel' &&
                prevOriginThread.id !== originThread.id
            ) {
                // messages linked to different document thread
                return false;
            }
            return true;
        },
    },
    fields: {
        /**
         * Model for the component with the controls for RTC related settings.
         */
        callSettingsMenu: one('CallSettingsMenu', {
            compute() {
                if (this.isCallSettingsMenuOpen) {
                    return {};
                }
                return clear();
            },
            inverse: 'threadViewOwner',
        }),
        channelMemberListView: one('ChannelMemberListView', {
            compute() {
                if (this.thread && this.thread.hasMemberListFeature && this.hasMemberList && this.isMemberListOpened) {
                    return {};
                }
                return clear();
            },
            inverse: 'threadViewOwner',
        }),
        compact: attr({
            related: 'threadViewer.compact',
        }),
        /**
         * List of component hints. Hints contain information that help
         * components make UI/UX decisions based on their UI state.
         * For instance, on receiving new messages and the last message
         * is visible, it should auto-scroll to this new last message.
         *
         * Format of a component hint:
         *
         *   {
         *       type: {string} the name of the component hint. Useful
         *                      for components to dispatch behaviour
         *                      based on its type.
         *       data: {Object} data related to the component hint.
         *                      For instance, if hint suggests to scroll
         *                      to a certain message, data may contain
         *                      message id.
         *   }
         */
        componentHintList: attr({
            default: [],
        }),
        composerView: one('ComposerView', {
            compute() {
                if (!this.thread || this.thread.mailbox) {
                    return clear();
                }
                if (this.threadViewer && this.threadViewer.chatter) {
                    return clear();
                }
                return {};
            },
            inverse: 'threadView',
        }),
        /**
         * Determines which extra class this thread view component should have.
         */
        extraClass: attr({
            related: 'threadViewer.extraClass',
        }),
        /**
         * Determines whether this thread viewer has a member list.
         * Only makes sense if thread.hasMemberListFeature is true.
         */
        hasMemberList: attr({
            related: 'threadViewer.hasMemberList',
        }),
        /**
         * Determines whether this thread view should squash close messages.
         * See `_shouldMessageBeSquashed` for which conditions are considered
         * to determine if messages are "close" to each other.
         */
        hasSquashCloseMessages: attr({
            compute() {
                return Boolean(this.threadViewer && !this.threadViewer.chatter && this.thread && !this.thread.mailbox);
            },
        }),
        /**
         * Determines whether this thread view has a top bar.
         */
        hasTopbar: attr({
            related: 'threadViewer.hasTopbar',
        }),
        isCallSettingsMenuOpen: attr({
            default: false,
        }),
        isComposerFocused: attr({
            related: 'composerView.isFocused',
        }),
        /**
         * States whether `this.threadCache` is currently loading messages.
         *
         * This field is related to `this.threadCache.isLoading` but with a
         * delay on its update to avoid flickering on the UI.
         *
         * It is computed through `_onThreadCacheIsLoadingChanged` and it should
         * otherwise be considered read-only.
         */
        isLoading: attr({
            default: false,
        }),
        /**
         * Determines whether the member list of this thread is opened.
         * Only makes sense if hasMemberListFeature and hasMemberList are true.
         */
        isMemberListOpened: attr({
            default: false,
        }),
        /**
         * States whether `this` is aware of `this.threadCache` currently
         * loading messages, but `this` is not yet ready to display that loading
         * on the UI.
         *
         * This field is computed through `_onThreadCacheIsLoadingChanged` and
         * it should otherwise be considered read-only.
         *
         * @see `this.isLoading`
         */
        isPreparingLoading: attr({
            default: false,
        }),
        /**
         * Determines whether `this` should automatically scroll on receiving
         * a new message. Detection of new message is done through the component
         * hint `message-received`.
         */
        hasAutoScrollOnMessageReceived: attr({
            default: true,
        }),
        hasComposerThreadName: attr({
            compute() {
                if (this.threadViewer.discuss) {
                    return this.threadViewer.discuss.activeThread === this.messaging.inbox.thread;
                }
                return clear();
            },
            default: false,
        }),
        /**
         * If set, determines whether the composer should display status of
         * members typing on related thread. When this prop is not provided,
         * it defaults to composer component default value.
         */
        hasComposerThreadTyping: attr({
            compute() {
                if (this.threadViewer.threadView_hasComposerThreadTyping !== undefined) {
                    return this.threadViewer.threadView_hasComposerThreadTyping;
                }
                return clear();
            },
            default: false,
        }),
        /**
         * Last message in the context of the currently displayed thread cache.
         */
        lastMessage: one('Message', {
            related: 'thread.lastMessage',
        }),
        lastMessageListViewItem: one('MessageListViewItem', {
            compute() {
                if (!this.messageListView) {
                    return clear();
                }
                const { length, [length - 1]: messageListViewItem } = this.messageListView.messageListViewItems;
                return messageListViewItem;
            },
            inverse: 'threadViewOwnerAsLastMessageListViewItem',
        }),
        /**
         * Most recent message in this ThreadView that has been shown to the
         * current partner in the currently displayed thread cache.
         */
        lastVisibleMessage: one('Message'),
        loaderTimeout: attr(),
        messageListView: one('MessageListView', {
            compute() {
                return (
                    (this.thread && this.thread.isTemporary) ||
                    (this.threadCache && this.threadCache.isLoaded)
                ) ? {} : clear();
            },
            inverse: 'threadViewOwner',
        }),
        messages: many('Message', {
            related: 'threadCache.messages',
        }),
        /**
         * States the order mode of the messages on this thread view.
         * Either 'asc', or 'desc'.
         */
        order: attr({
            related: 'threadViewer.order',
        }),
        /**
         * Determines the message that's currently being replied to.
         */
        replyingToMessageView: one('MessageView'),
        /**
         * Determines the call view of this thread.
         */
        callView: one('CallView', {
            compute() {
                return (this.thread && this.thread.model === 'mail.channel' && this.thread.rtcSessions.length > 0)
                    ? {}
                    : clear();
            },
            inverse: 'threadView',
        }),
        /**
         * Determines the `Thread` currently displayed by `this`.
         */
        thread: one('Thread', {
            inverse: 'threadViews',
            related: 'threadViewer.thread',
        }),
        /**
         * States the `ThreadCache` currently displayed by `this`.
         */
        threadCache: one('ThreadCache', {
            inverse: 'threadViews',
            related: 'threadViewer.threadCache',
        }),
        threadCacheInitialScrollHeight: attr({
            compute() {
                if (!this.threadCache) {
                    return clear();
                }
                const threadCacheInitialScrollHeight = this.threadCacheInitialScrollHeights[this.threadCache.localId];
                if (threadCacheInitialScrollHeight !== undefined) {
                    return threadCacheInitialScrollHeight;
                }
                return clear();
            },
        }),
        threadCacheInitialScrollPosition: attr({
            compute() {
                if (!this.threadCache) {
                    return clear();
                }
                const threadCacheInitialScrollPosition = this.threadCacheInitialScrollPositions[this.threadCache.localId];
                if (threadCacheInitialScrollPosition !== undefined) {
                    return threadCacheInitialScrollPosition;
                }
                return clear();
            },
        }),
        /**
         * List of saved initial scroll heights of thread caches.
         */
        threadCacheInitialScrollHeights: attr({
            default: {},
            related: 'threadViewer.threadCacheInitialScrollHeights',
        }),
        /**
         * List of saved initial scroll positions of thread caches.
         */
        threadCacheInitialScrollPositions: attr({
            default: {},
            related: 'threadViewer.threadCacheInitialScrollPositions',
        }),
        /**
         * Determines the `ThreadViewer` currently managing `this`.
         */
        threadViewer: one('ThreadViewer', {
            identifying: true,
            inverse: 'threadView',
        }),
        /**
         * Determines the top bar of this thread view, if any.
         */
        topbar: one('ThreadViewTopbar', {
            compute() {
                return this.hasTopbar ? {} : clear();
            },
            inverse: 'threadView',
        }),
    },
    onChanges: [
        {
            dependencies: ['threadCache'],
            methodName: '_onThreadCacheChanged',
        },
        {
            dependencies: ['threadCache.isLoading'],
            methodName: '_onThreadCacheIsLoadingChanged',
        },
        {
            dependencies: ['isComposerFocused', 'lastMessage', 'thread.lastNonTransientMessage', 'lastVisibleMessage', 'threadCache'],
            methodName: '_computeThreadShouldBeSetAsSeen',
        },
    ],
});
