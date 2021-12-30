/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';

const { Component } = owl;
const { onWillPatch, useRef } = owl.hooks;

export class MessageList extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        /**
         * States whether there was at least one programmatic scroll since the
         * last scroll event was handled (which is particularly async due to
         * throttled behavior).
         * Useful to avoid loading more messages or to incorrectly disabling the
         * auto-scroll feature when the scroll was not made by the user.
         */
        this._isLastScrollProgrammatic = false;
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
        for (const hint of this.threadView.componentHintList) {
            switch (hint.type) {
                case 'change-of-thread-cache':
                case 'member-list-hidden':
                    // thread just became visible, the goal is to restore its
                    // saved position if it exists or scroll to the end
                    this._adjustScrollFromModel();
                    break;
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
            if (this.threadView) {
                this.threadView.markComponentHintProcessed(hint);
            }
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
        if (this._getScrollableElement().scrollTop === value) {
            return;
        }
        this._isLastScrollProgrammatic = true;
        this._getScrollableElement().scrollTop = value;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adjustScrollForExtraMessagesAtTheEnd() {
        if (!this._getScrollableElement() || !this.threadView.hasScrollAdjust) {
            return;
        }
        if (!this.threadView.hasAutoScrollOnMessageReceived) {
            if (this.threadView.order === 'desc' && this._willPatchSnapshot) {
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
        if (
            !this._getScrollableElement() ||
            !this.threadView.hasScrollAdjust ||
            !this._willPatchSnapshot ||
            this.threadView.order === 'desc'
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
        if (!this._getScrollableElement() || !this.threadView.hasScrollAdjust) {
            return;
        }
        if (
            this.threadView.threadCacheInitialScrollPosition !== undefined &&
            this._getScrollableElement().scrollHeight === this.threadView.threadCacheInitialScrollHeight
        ) {
            this.setScrollTop(this.threadView.threadCacheInitialScrollPosition);
            return;
        }
        this._scrollToEnd();
        return;
    }

    /**
     * @private
     */
    _checkMostRecentMessageIsVisible() {
        if (!this.threadView) {
            return;
        }
        const { lastMessageView } = this.threadView;
        if (lastMessageView && lastMessageView.component && lastMessageView.component.isPartiallyVisible()) {
            this.threadView.handleVisibleMessage(lastMessageView.message);
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
     * @private
     */
    _loadMore() {
        if (!this.threadView.threadCache) {
            return;
        }
        this.threadView.threadCache.loadMoreMessages();
    }

    /**
     * Scrolls to the end of the list.
     *
     * @private
     */
    _scrollToEnd() {
        this.setScrollTop(this.threadView.order === 'asc' ? this._getScrollableElement().scrollHeight - this._getScrollableElement().clientHeight : 0);
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
        this._loadMore();
    }

    /**
     * @private
     */
    _onClickRetryLoadMoreMessages() {
        if (!this.threadView) {
            return;
        }
        if (!this.threadView.threadCache) {
            return;
        }
        this.threadView.threadCache.update({ hasLoadingFailed: false });
        this._loadMore();
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
        if (!this._getScrollableElement()) {
            // could be unmounted in the meantime (due to throttled behavior)
            return;
        }
        const scrollTop = this._getScrollableElement().scrollTop;
        this.messaging.messagingBus.trigger('o-component-message-list-scrolled', {
            orderedMessages: this.threadView.orderedMessages,
            scrollTop,
            thread: this.threadView.thread,
            threadViewer: this.threadView,
        });
        if (!this._isLastScrollProgrammatic && this.threadView) {
            // Margin to compensate for inaccurate scrolling to bottom and height
            // flicker due height change of composer area.
            const margin = 30;
            // Automatically scroll to new received messages only when the list is
            // currently fully scrolled.
            const hasAutoScrollOnMessageReceived = (this.threadVieworder === 'asc')
                ? scrollTop >= this._getScrollableElement().scrollHeight - this._getScrollableElement().clientHeight - margin
                : scrollTop <= margin;
            this.threadView.update({ hasAutoScrollOnMessageReceived });
        }
        if (this.threadView.threadViewer) {
            this.threadView.threadViewer.saveThreadCacheScrollHeightAsInitial(this._getScrollableElement().scrollHeight, this.threadView.threadCache);
            this.threadView.threadViewer.saveThreadCacheScrollPositionsAsInitial(scrollTop, this.threadView.threadCache);
        }
        if (!this._isLastScrollProgrammatic && this._isLoadMoreVisible()) {
            this._loadMore();
        }
        this._checkMostRecentMessageIsVisible();
        this._isLastScrollProgrammatic = false;
    }

}

Object.assign(MessageList, {
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
        hasScrollAdjust: Boolean,
        threadViewLocalId: String,
    },
    template: 'mail.MessageList',
});

registerMessagingComponent(MessageList, {
    extraCacheList: [
        'threadView.componentHintList',
        'threadView.handleVisibleMessage',
        'threadView.hasAutoScrollOnMessageReceived',
        'threadView.hasScrollAdjust',
        'threadView.lastMessageView.component',
        'threadView.lastMessageView.message.id',
        'threadView.lastVisibleMessage.id',
        'threadView.markComponentHintProcessed',
        'threadView.messaging.messagingBus',
        'threadView.modelManager',
        'threadView.order',
        'threadView.thread',
        'threadView.threadCache.orderedMessages',
        'threadView.threadCacheInitialScrollHeight',
        'threadView.threadCacheInitialScrollPosition',
        'threadView.threadViewer',
        'threadView.update',
    ],
    modelName: 'ThreadView',
    propNameAsRecordLocalId: 'threadViewLocalId',
    recordName: 'threadView',
});
