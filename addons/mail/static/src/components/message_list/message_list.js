/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRenderedValues } from '@mail/component_hooks/use_rendered_values';
import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Transition } from "@web/core/transition";

const { Component, onWillPatch, useRef } = owl;

export class MessageList extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'MessageListView' });
        /**
         * Reference of the "load more" item. Useful to trigger load more
         * on scroll when it becomes visible.
         */
        this._loadMoreRef = useRef('loadMore');
        /**
         * Snapshot computed during willPatch, which is used by patched.
         */
        this._willPatchSnapshot = undefined;
        this._onScrollThrottled = _.throttle(this._onScrollThrottled.bind(this), 100);
        /**
         * State used by the component at the time of the render. Useful to
         * properly handle async code.
         */
        this._lastRenderedValues = useRenderedValues(() => {
            const messageListView = this.messageListView;
            const threadView = messageListView && messageListView.threadViewOwner;
            const thread = threadView && threadView.thread;
            const threadCache = threadView && threadView.threadCache;
            return {
                componentHintList: threadView ? [...threadView.componentHintList] : [],
                hasAutoScrollOnMessageReceived: threadView && threadView.hasAutoScrollOnMessageReceived,
                hasScrollAdjust: this.props.hasScrollAdjust,
                messageListView,
                order: threadView && threadView.order,
                orderedMessages: threadCache ? [...threadCache.orderedMessages] : [],
                thread,
                threadCache,
                threadCacheInitialScrollHeight: threadView && threadView.threadCacheInitialScrollHeight,
                threadCacheInitialScrollPosition: threadView && threadView.threadCacheInitialScrollPosition,
            };
        });
        // useUpdate must be defined after useRenderedValues, indeed they both
        // use onMounted/onPatched, and the calls from useRenderedValues must
        // happen first to save the values before useUpdate accesses them.
        useUpdate({ func: () => this._update() });
        onWillPatch(() => this._willPatch());
    }

    _willPatch() {
        this._willPatchSnapshot = {
            scrollHeight: this._getScrollableElement().scrollHeight,
            scrollTop: this._getScrollableElement().scrollTop,
        };
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

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
        const { componentHintList, messageListView } = this._lastRenderedValues();
        if (!messageListView || !messageListView.exists()) {
            return;
        }
        for (const hint of componentHintList) {
            switch (hint.type) {
                case 'change-of-thread-cache':
                case 'member-list-hidden':
                    // thread just became visible, the goal is to restore its
                    // saved position if it exists or scroll to the end
                    this._adjustScrollFromModel();
                    break;
                case 'message-posted':
                case 'message-received':
                case 'messages-loaded':
                case 'new-messages-loaded':
                    // messages have been added at the end, either scroll to the
                    // end or keep the current position
                    this._adjustScrollForExtraMessagesAtTheEnd();
                    break;
                case 'more-messages-loaded':
                    // messages have been added at the start, keep the current
                    // position
                    this._adjustScrollForExtraMessagesAtTheStart();
                    break;
            }
            messageListView.threadViewOwner.markComponentHintProcessed(hint);
        }
        this._willPatchSnapshot = undefined;
    }

    /**
     * @returns {integer}
     */
    getScrollHeight() {
        return this._getScrollableElement().scrollHeight;
    }

    /**
     * @returns {integer}
     */
    getScrollTop() {
        return this._getScrollableElement().scrollTop;
    }

    /**
     * @param {integer} value
     */
    setScrollTop(value) {
        const { messageListView } = this._lastRenderedValues();
        if (this._getScrollableElement().scrollTop === value) {
            return;
        }
        messageListView.update({ isLastScrollProgrammatic: true });
        this._getScrollableElement().scrollTop = value;
    }

    /**
     * @returns {MessageListView}
     */
    get messageListView() {
        return this.messaging && this.messaging.models['MessageListView'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adjustScrollForExtraMessagesAtTheEnd() {
        const {
            hasAutoScrollOnMessageReceived,
            hasScrollAdjust,
            order,
        } = this._lastRenderedValues();
        if (!this._getScrollableElement() || !hasScrollAdjust) {
            return;
        }
        if (!hasAutoScrollOnMessageReceived) {
            if (order === 'desc' && this._willPatchSnapshot) {
                const { scrollHeight, scrollTop } = this._willPatchSnapshot;
                this.setScrollTop(this._getScrollableElement().scrollHeight - scrollHeight + scrollTop);
            }
            return;
        }
        this._scrollToEnd();
    }

    /**
     * @private
     */
    _adjustScrollForExtraMessagesAtTheStart() {
        const {
            hasScrollAdjust,
            order,
        } = this._lastRenderedValues();
        if (
            !this._getScrollableElement() ||
            !hasScrollAdjust ||
            !this._willPatchSnapshot ||
            order === 'desc'
        ) {
            return;
        }
        const { scrollHeight, scrollTop } = this._willPatchSnapshot;
        this.setScrollTop(this._getScrollableElement().scrollHeight - scrollHeight + scrollTop);
    }

    /**
     * @private
     */
    _adjustScrollFromModel() {
        const {
            hasScrollAdjust,
            threadCacheInitialScrollHeight,
            threadCacheInitialScrollPosition,
        } = this._lastRenderedValues();
        if (!this._getScrollableElement() || !hasScrollAdjust) {
            return;
        }
        if (
            threadCacheInitialScrollPosition !== undefined &&
            this._getScrollableElement().scrollHeight === threadCacheInitialScrollHeight
        ) {
            this.setScrollTop(threadCacheInitialScrollPosition);
            return;
        }
        this._scrollToEnd();
        return;
    }

    /**
     * @private
     */
    _checkMostRecentMessageIsVisible() {
        const { messageListView } = this._lastRenderedValues();
        if (!messageListView || !messageListView.exists()) {
            return;
        }
        const { lastMessageView } = messageListView.threadViewOwner;
        if (lastMessageView && lastMessageView.component && lastMessageView.component.isPartiallyVisible()) {
            messageListView.threadViewOwner.handleVisibleMessage(lastMessageView.message);
        }
    }

    /**
     * @private
     * @returns {Element|undefined} Scrollable Element
     */
    _getScrollableElement() {
        if (this.props.getScrollableElement) {
            return this.props.getScrollableElement();
        } else {
            return this.root.el;
        }
    }

    /**
     * @private
     * @returns {boolean}
     */
    _isLoadMoreVisible() {
        const loadMore = this._loadMoreRef.el;
        if (!loadMore) {
            return false;
        }
        const loadMoreRect = loadMore.getBoundingClientRect();
        const elRect = this._getScrollableElement().getBoundingClientRect();
        const isInvisible = loadMoreRect.top > elRect.bottom || loadMoreRect.bottom < elRect.top;
        return !isInvisible;
    }

    /**
     * Scrolls to the end of the list.
     *
     * @private
     */
    _scrollToEnd() {
        const { order } = this._lastRenderedValues();
        this.setScrollTop(order === 'asc' ? this._getScrollableElement().scrollHeight - this._getScrollableElement().clientHeight : 0);
    }

    /**
     * @private
     */
    _update() {
        this.adjustFromComponentHints();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickLoadMore(ev) {
        ev.preventDefault();
        const { threadCache } = this._lastRenderedValues();
        if (!threadCache || !threadCache.exists()) {
            return;
        }
        threadCache.loadMoreMessages();
    }

    /**
     * @private
     */
    _onClickRetryLoadMoreMessages() {
        const { threadCache } = this._lastRenderedValues();
        if (!threadCache || !threadCache.exists()) {
            return;
        }
        threadCache.update({ hasLoadingFailed: false });
        threadCache.loadMoreMessages();
    }

    /**
     * @private
     * @param {ScrollEvent} ev
     */
    onScroll(ev) {
        this._onScrollThrottled(ev);
    }

    /**
     * @private
     * @param {ScrollEvent} ev
     */
    _onScrollThrottled(ev) {
        const {
            messageListView,
            orderedMessages,
            thread,
            threadCache,
        } = this._lastRenderedValues();
        if (!messageListView || !messageListView.exists()) {
            return;
        }
        if (!this._getScrollableElement()) {
            // could be unmounted in the meantime (due to throttled behavior)
            return;
        }
        const scrollTop = this._getScrollableElement().scrollTop;
        this.messaging.messagingBus.trigger('o-component-message-list-scrolled', {
            orderedMessages,
            scrollTop,
            thread,
            threadViewer: messageListView.threadViewOwner.threadViewer,
        });
        messageListView.update({
            clientHeight: this._getScrollableElement().clientHeight,
            scrollHeight: this._getScrollableElement().scrollHeight,
            scrollTop: this._getScrollableElement().scrollTop,
        });
        if (!messageListView.isLastScrollProgrammatic) {
            // Automatically scroll to new received messages only when the list is
            // currently fully scrolled.
            const hasAutoScrollOnMessageReceived = messageListView.isAtEnd;
            messageListView.threadViewOwner.update({ hasAutoScrollOnMessageReceived });
        }
        messageListView.threadViewOwner.threadViewer.saveThreadCacheScrollHeightAsInitial(this._getScrollableElement().scrollHeight, threadCache);
        messageListView.threadViewOwner.threadViewer.saveThreadCacheScrollPositionsAsInitial(scrollTop, threadCache);
        if (
            !messageListView.isLastScrollProgrammatic &&
            this._isLoadMoreVisible() &&
            threadCache &&
            threadCache.exists()
        ) {
            threadCache.loadMoreMessages();
        }
        this._checkMostRecentMessageIsVisible();
        messageListView.update({ isLastScrollProgrammatic: false });
    }

}

Object.assign(MessageList, {
    components: { Transition },
    defaultProps: {
        hasScrollAdjust: true,
    },
    props: {
        /**
         * Function returns the exact scrollable element from the parent
         * to manage proper scroll heights which affects the load more messages.
         */
        getScrollableElement: {
            type: Function,
            optional: true,
        },
        hasScrollAdjust: {
            type: Boolean,
            optional: true,
        },
        localId: String,
    },
    template: 'mail.MessageList',
});

registerMessagingComponent(MessageList);
