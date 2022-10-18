/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useRenderedValues } from '@mail/component_hooks/use_rendered_values';
import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Transition } from "@web/core/transition";

const { Component, onWillPatch } = owl;

export class MessageList extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'loadMoreRef', refName: 'loadMore' });
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
            const threadView = messageListView.threadViewOwner;
            const thread = threadView && threadView.thread;
            const threadCache = threadView && threadView.threadCache;
            return {
                hasAutoScrollOnMessageReceived: threadView && threadView.hasAutoScrollOnMessageReceived,
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
        if (!this.messageListView.exists()) {
            return;
        }
        this._willPatchSnapshot = {
            scrollHeight: this.messageListView.getScrollableElement().scrollHeight,
            scrollTop: this.messageListView.getScrollableElement().scrollTop,
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
        if (!this.messageListView.exists()) {
            return;
        }
        for (const hint of this.messageListView.threadViewOwner.componentHintList) {
            switch (hint.type) {
                case 'change-of-thread-cache':
                case 'member-list-hidden':
                case 'adjust-scroll':
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
            this.messageListView.threadViewOwner.markComponentHintProcessed(hint);
        }
        this._willPatchSnapshot = undefined;
    }

    /**
     * @param {integer} value
     */
    setScrollTop(value) {
        if (this.messageListView.getScrollableElement().scrollTop === value) {
            return;
        }
        this.messageListView.update({ isLastScrollProgrammatic: true });
        this.messageListView.getScrollableElement().scrollTop = value;
    }

    /**
     * @returns {MessageListView}
     */
    get messageListView() {
        return this.props.record;
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
            order,
        } = this._lastRenderedValues();
        if (!this.messageListView.getScrollableElement() || !this.messageListView.hasScrollAdjust) {
            return;
        }
        if (!hasAutoScrollOnMessageReceived) {
            if (order === 'desc' && this._willPatchSnapshot) {
                const { scrollHeight, scrollTop } = this._willPatchSnapshot;
                this.setScrollTop(this.messageListView.getScrollableElement().scrollHeight - scrollHeight + scrollTop);
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
            order,
        } = this._lastRenderedValues();
        if (
            !this.messageListView.getScrollableElement() ||
            !this.messageListView.hasScrollAdjust ||
            !this._willPatchSnapshot ||
            order === 'desc'
        ) {
            return;
        }
        const { scrollHeight, scrollTop } = this._willPatchSnapshot;
        this.setScrollTop(this.messageListView.getScrollableElement().scrollHeight - scrollHeight + scrollTop);
    }

    /**
     * @private
     */
    _adjustScrollFromModel() {
        const {
            threadCacheInitialScrollHeight,
            threadCacheInitialScrollPosition,
        } = this._lastRenderedValues();
        if (!this.messageListView.getScrollableElement() || !this.messageListView.hasScrollAdjust) {
            return;
        }
        if (
            threadCacheInitialScrollPosition !== undefined &&
            this.messageListView.getScrollableElement().scrollHeight === threadCacheInitialScrollHeight
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
        if (!this.messageListView.exists()) {
            return;
        }
        const { lastMessageView } = this.messageListView.threadViewOwner;
        if (lastMessageView && lastMessageView.component && lastMessageView.component.isPartiallyVisible()) {
            this.messageListView.threadViewOwner.handleVisibleMessage(lastMessageView.message);
        }
    }

    /**
     * @private
     * @returns {boolean}
     */
    _isLoadMoreVisible() {
        const loadMore = this.messageListView.loadMoreRef.el;
        if (!loadMore) {
            return false;
        }
        const loadMoreRect = loadMore.getBoundingClientRect();
        const elRect = this.messageListView.getScrollableElement().getBoundingClientRect();
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
        this.setScrollTop(order === 'asc' ? this.messageListView.getScrollableElement().scrollHeight - this.messageListView.getScrollableElement().clientHeight : 0);
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
            orderedMessages,
            thread,
            threadCache,
        } = this._lastRenderedValues();
        if (!this.messageListView.exists()) {
            return;
        }
        if (!this.messageListView.getScrollableElement()) {
            // could be unmounted in the meantime (due to throttled behavior)
            return;
        }
        const scrollTop = this.messageListView.getScrollableElement().scrollTop;
        this.messaging.messagingBus.trigger('o-component-message-list-scrolled', {
            orderedMessages,
            scrollTop,
            thread,
            threadViewer: this.messageListView.threadViewOwner.threadViewer,
        });
        this.messageListView.update({
            clientHeight: this.messageListView.getScrollableElement().clientHeight,
            scrollHeight: this.messageListView.getScrollableElement().scrollHeight,
            scrollTop: this.messageListView.getScrollableElement().scrollTop,
        });
        if (!this.messageListView.isLastScrollProgrammatic) {
            // Automatically scroll to new received messages only when the list is
            // currently fully scrolled.
            const hasAutoScrollOnMessageReceived = this.messageListView.isAtEnd;
            this.messageListView.threadViewOwner.update({ hasAutoScrollOnMessageReceived });
        }
        this.messageListView.threadViewOwner.threadViewer.saveThreadCacheScrollHeightAsInitial(this.messageListView.getScrollableElement().scrollHeight, threadCache);
        this.messageListView.threadViewOwner.threadViewer.saveThreadCacheScrollPositionsAsInitial(scrollTop, threadCache);
        if (
            !this.messageListView.isLastScrollProgrammatic &&
            this._isLoadMoreVisible() &&
            threadCache &&
            threadCache.exists()
        ) {
            threadCache.loadMoreMessages();
        }
        this._checkMostRecentMessageIsVisible();
        this.messageListView.update({ isLastScrollProgrammatic: false });
    }

}

Object.assign(MessageList, {
    components: { Transition },
    props: { record: Object },
    template: 'mail.MessageList',
});

registerMessagingComponent(MessageList);
