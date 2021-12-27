/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { RecordDeletedError } from '@mail/model/model_errors';
import { attr, many2many, many2one, one2many, one2one } from '@mail/model/model_field';
import { clear, insertAndReplace, link, replace, unlink, update } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

registerModel({
    name: 'ThreadView',
    identifyingFields: ['threadViewer'],
    lifecycleHooks: {
        _created() {
            this._loaderTimeout = undefined;
        },
        _willDelete() {
            this.env.browser.clearTimeout(this._loaderTimeout);
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
                this.update({ lastVisibleMessage: link(message) });
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
        /**
         * Starts editing the last message of this thread from the current user.
         */
        startEditingLastMessageFromCurrentUser() {
            const messageViews = this.messageViews;
            messageViews.reverse();
            const messageView = messageViews.find(messageViews => messageViews.message.isCurrentUserOrGuestAuthor && messageViews.message.canBeDeleted);
            if (messageView) {
                messageView.startEditing();
            }
        },
        /**
         * @private
         */
        _computeRtcCallViewer() {
            return (this.thread && this.thread.model === 'mail.channel' && this.thread.rtcSessions.length > 0)
                ? insertAndReplace()
                : clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeComposerView() {
            if (!this.thread || this.thread.model === 'mail.box') {
                return clear();
            }
            if (this.threadViewer && this.threadViewer.chatter) {
                return clear();
            }
            return insertAndReplace();
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasSquashCloseMessages() {
            return Boolean(this.threadViewer && !this.threadViewer.chatter && this.thread && this.thread.model !== 'mail.box');
        },
        /**
         * @private
         * @returns {MessageView[]}
         */
        _computeMessageViews() {
            if (!this.threadCache) {
                return clear();
            }
            const orderedMessages = this.threadCache.orderedNonEmptyMessages;
            if (this.order === 'desc') {
                orderedMessages.reverse();
            }
            const messageViewsData = [];
            let prevMessage;
            for (const message of orderedMessages) {
                messageViewsData.push({
                    isSquashed: this._shouldMessageBeSquashed(prevMessage, message),
                    message: replace(message),
                });
                prevMessage = message;
            }
            return insertAndReplace(messageViewsData);
        },
        /**
         * @private
         * @returns {integer|undefined}
         */
        _computeThreadCacheInitialScrollHeight() {
            if (!this.threadCache) {
                return clear();
            }
            const threadCacheInitialScrollHeight = this.threadCacheInitialScrollHeights[this.threadCache.localId];
            if (threadCacheInitialScrollHeight !== undefined) {
                return threadCacheInitialScrollHeight;
            }
            return clear();
        },
        /**
         * @private
         * @returns {integer|undefined}
         */
        _computeThreadCacheInitialScrollPosition() {
            if (!this.threadCache) {
                return clear();
            }
            const threadCacheInitialScrollPosition = this.threadCacheInitialScrollPositions[this.threadCache.localId];
            if (threadCacheInitialScrollPosition !== undefined) {
                return threadCacheInitialScrollPosition;
            }
            return clear();
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
            if (!this.hasComposerFocus) {
                // FIXME condition should not be on "composer is focused" but "threadView is active"
                // See task-2277543
                return;
            }
            if (this.messaging.currentGuest) {
                return;
            }
            this.thread.markAsSeen(this.thread.lastNonTransientMessage).catch(e => {
                // prevent crash when executing compute during destroy
                if (!(e instanceof RecordDeletedError)) {
                    throw e;
                }
            });
        },
        /**
         * @private
         */
        _computeTopbar() {
            return this.hasTopbar ? insertAndReplace() : clear();
        },
        /**
         * @private
         */
        _onThreadCacheChanged() {
            // clear obsolete hints
            this.update({ componentHintList: clear() });
            this.addComponentHint('change-of-thread-cache');
            if (this.threadCache) {
                this.threadCache.update({
                    isCacheRefreshRequested: true,
                    isMarkAllAsReadRequested: true,
                });
            }
            this.update({ lastVisibleMessage: unlink() });
        },
        /**
         * @private
         */
        _onThreadCacheIsLoadingChanged() {
            if (this.threadCache && this.threadCache.isLoading) {
                if (!this.isLoading && !this.isPreparingLoading) {
                    this.update({ isPreparingLoading: true });
                    this.async(() =>
                        new Promise(resolve => {
                            this._loaderTimeout = this.env.browser.setTimeout(resolve, 400);
                        }
                    )).then(() => {
                        const isLoading = this.threadCache
                            ? this.threadCache.isLoading
                            : false;
                        this.update({ isLoading, isPreparingLoading: false });
                    });
                }
                return;
            }
            this.env.browser.clearTimeout(this._loaderTimeout);
            this.update({ isLoading: false, isPreparingLoading: false });
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
        compact: attr({
            related: 'threadViewer.compact',
        }),
        /**
         * States which channel invitation form is operating this thread view.
         * Only applies if this thread is a channel.
         */
        channelInvitationForm: one2one('ChannelInvitationForm', {
            inverse: 'threadView',
            isCausal: true,
        }),
        /**
         * States the OWL component of this thread view.
         */
        component: attr(),
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
        composerView: one2one('ComposerView', {
            compute: '_computeComposerView',
            inverse: 'threadView',
            isCausal: true,
        }),
        /**
         * Determines which extra class this thread view component should have.
         */
        extraClass: attr({
            related: 'threadViewer.extraClass',
        }),
        hasComposerFocus: attr({
            related: 'composerView.hasFocus',
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
            compute: '_computeHasSquashCloseMessages',
        }),
        /**
         * Determines whether this thread view has a top bar.
         */
        hasTopbar: attr({
            related: 'threadViewer.hasTopbar',
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
        /**
         * Last message in the context of the currently displayed thread cache.
         */
        lastMessage: many2one('Message', {
            related: 'thread.lastMessage',
        }),
        /**
         * Most recent message in this ThreadView that has been shown to the
         * current partner in the currently displayed thread cache.
         */
        lastVisibleMessage: many2one('Message'),
        /**
         * States the OWL MessageList component of this thread view
         */
        messageListComponent: attr(),
        messages: many2many('Message', {
            related: 'threadCache.messages',
        }),
        /**
         * States the message views used to display this messages.
         */
        messageViews: one2many('MessageView', {
            compute: '_computeMessageViews',
            inverse: 'threadView',
            isCausal: true,
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
        replyingToMessageView: many2one('MessageView'),
        /**
         * Determines the Rtc call viewer of this thread.
         */
        rtcCallViewer: one2one('RtcCallViewer', {
            compute: '_computeRtcCallViewer',
            inverse: 'threadView',
            isCausal: true,
            readonly: true,
        }),
        /**
         * Determines the `Thread` currently displayed by `this`.
         */
        thread: many2one('Thread', {
            inverse: 'threadViews',
            readonly: true,
            related: 'threadViewer.thread',
        }),
        /**
         * States the `ThreadCache` currently displayed by `this`.
         */
        threadCache: many2one('ThreadCache', {
            inverse: 'threadViews',
            readonly: true,
            related: 'threadViewer.threadCache',
        }),
        threadCacheInitialScrollHeight: attr({
            compute: '_computeThreadCacheInitialScrollHeight',
        }),
        threadCacheInitialScrollPosition: attr({
            compute: '_computeThreadCacheInitialScrollPosition',
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
        threadViewer: one2one('ThreadViewer', {
            inverse: 'threadView',
            readonly: true,
            required: true,
        }),
        /**
         * Determines the top bar of this thread view, if any.
         */
        topbar: one2one('ThreadViewTopbar', {
            compute: '_computeTopbar',
            inverse: 'threadView',
            isCausal: true,
            readonly: true,
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['threadCache'],
            methodName: '_onThreadCacheChanged',
        }),
        new OnChange({
            dependencies: ['threadCache.isLoading'],
            methodName: '_onThreadCacheIsLoadingChanged',
        }),
        new OnChange({
            dependencies: ['hasComposerFocus', 'lastMessage', 'thread.lastNonTransientMessage', 'lastVisibleMessage', 'threadCache'],
            methodName: '_computeThreadShouldBeSetAsSeen',
        }),
    ],
});
