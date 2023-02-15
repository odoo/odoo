/** @odoo-module **/

import { attr, clear, many, one, Model } from "@mail/model";

Model({
    name: "MessageListView",
    recordMethods: {
        /**
         * Update the scroll position of the message list.
         * This is not done in patched/mounted hooks because scroll position is
         * dependent on UI globally. To illustrate, imagine following UI:
         *
         * +----------+ < viewport top = scrollable top
         * | message  |
         * |   list   |
         * |          |
         * +----------+ < scrolltop = viewport bottom = scrollable bottom
         *
         * Now if a composer is mounted just below the message list, it is shrinked
         * and scrolltop is altered as a result:
         *
         * +----------+ < viewport top = scrollable top
         * | message  |
         * |   list   | < scrolltop = viewport bottom  <-+
         * |          |                                  |-- dist = composer height
         * +----------+ < scrollable bottom            <-+
         * +----------+
         * | composer |
         * +----------+
         *
         * Because of this, the scroll position must be changed when whole UI
         * is rendered. To make this simpler, this is done when <ThreadView/>
         * component is patched. This is acceptable when <ThreadView/> has a
         * fixed height, which is the case for the moment. task-2358066
         */
        adjustFromComponentHints() {
            for (const hint of this.threadViewOwner.componentHintList) {
                switch (hint.type) {
                    case "change-of-thread-cache":
                    case "member-list-hidden":
                    case "adjust-scroll":
                        // thread just became visible, the goal is to restore its
                        // saved position if it exists or scroll to the end
                        this.adjustScrollFromModel();
                        break;
                    case "message-posted":
                    case "message-received":
                    case "messages-loaded":
                    case "new-messages-loaded":
                        // messages have been added at the end, either scroll to the
                        // end or keep the current position
                        this.adjustScrollForExtraMessagesAtTheEnd();
                        break;
                    case "more-messages-loaded":
                        // messages have been added at the start, keep the current
                        // position
                        this.adjustScrollForExtraMessagesAtTheStart();
                        break;
                }
                this.threadViewOwner.markComponentHintProcessed(hint);
            }
            this.component._willPatchSnapshot = undefined;
        },
        adjustScrollForExtraMessagesAtTheEnd() {
            if (!this.getScrollableElement() || !this.hasScrollAdjust) {
                return;
            }
            if (!this.threadViewOwner.hasAutoScrollOnMessageReceived) {
                if (this.threadViewOwner.order === "desc" && this.component._willPatchSnapshot) {
                    const { scrollHeight, scrollTop } = this.component._willPatchSnapshot;
                    this.setScrollTop(
                        this.getScrollableElement().scrollHeight - scrollHeight + scrollTop
                    );
                }
                return;
            }
            this.scrollToEnd();
        },
        adjustScrollForExtraMessagesAtTheStart() {
            if (
                !this.getScrollableElement() ||
                !this.hasScrollAdjust ||
                !this.component._willPatchSnapshot ||
                this.threadViewOwner.order === "desc"
            ) {
                return;
            }
            const { scrollHeight, scrollTop } = this.component._willPatchSnapshot;
            this.setScrollTop(this.getScrollableElement().scrollHeight - scrollHeight + scrollTop);
        },
        adjustScrollFromModel() {
            if (!this.getScrollableElement() || !this.hasScrollAdjust) {
                return;
            }
            if (
                this.threadViewOwner.threadCacheInitialScrollPosition !== undefined &&
                this.getScrollableElement().scrollHeight ===
                    this.threadViewOwner.threadCacheInitialScrollHeight
            ) {
                this.setScrollTop(this.threadViewOwner.threadCacheInitialScrollPosition);
                return;
            }
            this.scrollToEnd();
        },
        checkMostRecentMessageIsVisible() {
            if (!this.exists()) {
                return;
            }
            if (
                this.threadViewOwner.lastMessageListViewItem &&
                this.threadViewOwner.lastMessageListViewItem.isPartiallyVisible()
            ) {
                this.threadViewOwner.handleVisibleMessage(
                    this.threadViewOwner.lastMessageListViewItem.message
                );
            }
        },
        /**
         * @returns {Element|undefined}
         */
        getScrollableElement() {
            if (this.threadViewOwner.threadViewer.chatter) {
                return this.threadViewOwner.threadViewer.chatter.scrollPanelRef.el;
            }
            return this.component.root.el;
        },
        /**
         * @returns {boolean}
         */
        isLoadMoreVisible() {
            const loadMore = this.loadMoreRef.el;
            if (!loadMore) {
                return false;
            }
            const loadMoreRect = loadMore.getBoundingClientRect();
            const elRect = this.getScrollableElement().getBoundingClientRect();
            const isInvisible =
                loadMoreRect.top > elRect.bottom || loadMoreRect.bottom < elRect.top;
            return !isInvisible;
        },
        onClickRetryLoadMoreMessages() {
            if (!this.exists() || !this.thread) {
                return;
            }
            this.thread.cache.update({ hasLoadingFailed: false });
            this.thread.cache.loadMoreMessages();
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickLoadMore(ev) {
            ev.preventDefault();
            if (!this.exists() || !this.thread) {
                return;
            }
            this.thread.cache.loadMoreMessages();
        },
        onComponentUpdate() {
            if (!this.exists()) {
                return;
            }
            this.adjustFromComponentHints();
        },
        onScroll() {
            if (!this.exists()) {
                return;
            }
            this.scrollThrottle.do();
        },
        scrollToEnd() {
            this.setScrollTop(
                this.threadViewOwner.order === "asc"
                    ? this.getScrollableElement().scrollHeight -
                          this.getScrollableElement().clientHeight
                    : 0
            );
        },
        /**
         * @param {integer} value
         */
        setScrollTop(value) {
            if (this.getScrollableElement().scrollTop === value) {
                return;
            }
            this.update({ isLastScrollProgrammatic: true });
            this.getScrollableElement().scrollTop = value;
        },
        /**
         * @private
         */
        _onThrottledScroll() {
            if (!this.exists()) {
                return;
            }
            if (!this.getScrollableElement()) {
                // could be unmounted in the meantime (due to throttled behavior)
                return;
            }
            const scrollTop = this.getScrollableElement().scrollTop;
            this.messaging.messagingBus.trigger("o-component-message-list-scrolled", {
                orderedMessages: this.threadViewOwner.threadCache.orderedMessages,
                scrollTop,
                thread: this.threadViewOwner.thread,
                threadViewer: this.threadViewOwner.threadViewer,
            });
            this.update({
                clientHeight: this.getScrollableElement().clientHeight,
                scrollHeight: this.getScrollableElement().scrollHeight,
                scrollTop: this.getScrollableElement().scrollTop,
            });
            if (!this.isLastScrollProgrammatic) {
                // Automatically scroll to new received messages only when the list is
                // currently fully scrolled.
                const hasAutoScrollOnMessageReceived = this.isAtEnd;
                this.threadViewOwner.update({ hasAutoScrollOnMessageReceived });
            }
            this.threadViewOwner.threadViewer.saveThreadCacheScrollHeightAsInitial(
                this.getScrollableElement().scrollHeight,
                this.threadViewOwner.threadCache
            );
            this.threadViewOwner.threadViewer.saveThreadCacheScrollPositionsAsInitial(
                scrollTop,
                this.threadViewOwner.threadCache
            );
            if (
                !this.isLastScrollProgrammatic &&
                this.isLoadMoreVisible() &&
                this.threadViewOwner.threadCache
            ) {
                this.threadViewOwner.threadCache.loadMoreMessages();
            }
            this.checkMostRecentMessageIsVisible();
            this.update({ isLastScrollProgrammatic: false });
        },
    },
    fields: {
        clientHeight: attr(),
        /**
         * States the OWL component of this message list view
         */
        component: attr(),
        hasScrollAdjust: attr({
            default: true,
            compute() {
                if (this.threadViewOwner.threadViewer.chatter) {
                    return this.threadViewOwner.threadViewer.chatter.hasMessageListScrollAdjust;
                }
                return clear();
            },
        }),
        /**
         * States whether the message list scroll position is at the end of
         * the message list. Depending of the message list order, this could be
         * the top or the bottom.
         */
        isAtEnd: attr({
            compute() {
                /**
                 * The margin that we use to detect that the scrollbar is a the end of
                 * the threadView.
                 */
                const endThreshold = 30;
                if (this.threadViewOwner.order === "asc") {
                    return this.scrollTop >= this.scrollHeight - this.clientHeight - endThreshold;
                }
                return this.scrollTop <= endThreshold;
            },
        }),
        /**
         * States whether there was at least one programmatic scroll since the
         * last scroll event was handled (which is particularly async due to
         * throttled behavior).
         * Useful to avoid loading more messages or to incorrectly disabling the
         * auto-scroll feature when the scroll was not made by the user.
         */
        isLastScrollProgrammatic: attr({ default: false }),
        /**
         * Reference of the "load more" item. Useful to trigger load more
         * on scroll when it becomes visible.
         */
        loadMoreRef: attr(),
        /**
         * States the message views used to display this thread view owner's messages.
         */
        messageListViewItems: many("MessageListViewItem", {
            inverse: "messageListViewOwner",
            compute() {
                if (!this.threadViewOwner.threadCache) {
                    return clear();
                }
                const orderedMessages = this.threadViewOwner.threadCache.orderedNonEmptyMessages;
                if (this.threadViewOwner.order === "desc") {
                    orderedMessages.reverse();
                }
                const messageViewsData = [];
                let prevMessage;
                for (const message of orderedMessages) {
                    messageViewsData.push({
                        isSquashed: this.threadViewOwner._shouldMessageBeSquashed(
                            prevMessage,
                            message
                        ),
                        message,
                    });
                    prevMessage = message;
                }
                return messageViewsData;
            },
        }),
        scrollHeight: attr(),
        scrollThrottle: one("Throttle", {
            inverse: "messageListViewAsScroll",
            compute() {
                return { func: () => this._onThrottledScroll() };
            },
        }),
        scrollTop: attr(),
        thread: one("Thread", { related: "threadViewOwner.thread" }),
        threadViewOwner: one("ThreadView", { identifying: true, inverse: "messageListView" }),
    },
});
