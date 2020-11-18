odoo.define('mail/static/src/components/message_list/message_list.js', function (require) {
'use strict';

const components = {
    Message: require('mail/static/src/components/message/message.js'),
};
const useRefs = require('mail/static/src/component_hooks/use_refs/use_refs.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');
const useUpdate = require('mail/static/src/component_hooks/use_update/use_update.js');

const { Component } = owl;
const { useRef } = owl.hooks;

class MessageList extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const threadView = this.env.models['mail.thread_view'].get(props.threadViewLocalId);
            const thread = threadView ? threadView.thread : undefined;
            const threadCache = threadView ? threadView.threadCache : undefined;
            return {
                isDeviceMobile: this.env.messaging.device.isMobile,
                messages: threadCache
                    ? threadCache.orderedMessages.map(message => message.__state)
                    : [],
                thread: thread ? thread.__state : undefined,
                threadCache: threadCache ? threadCache.__state : undefined,
                threadView: threadView ? threadView.__state : undefined,
            };
        }, {
            compareDepth: {
                messages: 1,
            },
        });
        this._getRefs = useRefs();
        useUpdate({ func: () => this._update() });
        /**
         * Determine whether the auto-scroll on load is active or not. This
         * is useful to disable some times, such as when mounting message list
         * in ASC order: the initial scroll position is at the top of the
         * conversation, and most of the time the expected initial scroll
         * position should be at the bottom of the thread. During this time,
         * the programmatical scrolling should not trigger auto-load messages
         * on scroll.
         */
        this._isAutoLoadOnScrollActive = true;
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
    }

    willPatch() {
        const lastMessageRef = this.lastMessageRef;
        this._willPatchSnapshot = {
            isLastMessageVisible:
                lastMessageRef &&
                lastMessageRef.isBottomVisible({ offset: 10 }),
            scrollHeight: this.el.scrollHeight,
            scrollTop: this.el.scrollTop,
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
    async adjustFromComponentHints() {
        if (!this.threadView) {
            return;
        }
        if (!this.el) {
            return;
        }
        for (const hint of this.threadView.componentHintList) {
            switch (hint.type) {
                case 'change-of-thread-cache':
                    this._adjustFromChangeOfThreadCache(hint);
                    break;
                case 'home-menu-hidden':
                    this._adjustFromHomeMenuHidden(hint);
                    break;
                case 'home-menu-shown':
                    this._adjustFromHomeMenuShown(hint);
                    break;
                case 'messages-loaded':
                    this.threadView.markComponentHintProcessed(hint);
                    break;
                case 'message-received':
                    this._adjustFromMessageReceived(hint);
                    break;
                case 'more-messages-loaded':
                    this._adjustFromMoreMessagesLoaded(hint);
                    break;
                case 'new-messages-loaded':
                    this.threadView.markComponentHintProcessed(hint);
                    break;
            }
        }
        this._willPatchSnapshot = undefined;
    }

    /**
     * @param {mail.message} message
     * @returns {string}
     */
    getDateDay(message) {
        const date = message.date.format('YYYY-MM-DD');
        if (date === moment().format('YYYY-MM-DD')) {
            return this.env._t("Today");
        } else if (
            date === moment()
                .subtract(1, 'days')
                .format('YYYY-MM-DD')
        ) {
            return this.env._t("Yesterday");
        }
        return message.date.format('LL');
    }

    /**
     * @returns {integer}
     */
    getScrollHeight() {
        return this.el.scrollHeight;
    }

    /**
     * @returns {integer}
     */
    getScrollTop() {
        return this.el.scrollTop;
    }

    /**
     * @returns {mail/static/src/components/message/message.js|undefined}
     */
    get mostRecentMessageRef() {
        if (this.props.order === 'desc') {
            return this.messageRefs[0];
        }
        const { length: l, [l - 1]: mostRecentMessageRef } = this.messageRefs;
        return mostRecentMessageRef;
    }

    /**
     * @param {integer} messageId
     * @returns {mail/static/src/components/message/message.js|undefined}
     */
    messageRefFromId(messageId) {
        return this.messageRefs.find(ref => ref.message.id === messageId);
    }

    /**
     * Get list of sub-components Message, ordered based on prop `order`
     * (ASC/DESC).
     *
     * The asynchronous nature of OWL rendering pipeline may reveal disparity
     * between knowledgeable state of store between components. Use this getter
     * with extreme caution!
     *
     * Let's illustrate the disparity with a small example:
     *
     * - Suppose this component is aware of ordered (record) messages with
     *   following IDs: [1, 2, 3, 4, 5], and each (sub-component) messages map
     * each of these records.
     * - Now let's assume a change in store that translate to ordered (record)
     *   messages with following IDs: [2, 3, 4, 5, 6].
     * - Because store changes trigger component re-rendering by their "depth"
     *   (i.e. from parents to children), this component may be aware of
     *   [2, 3, 4, 5, 6] but not yet sub-components, so that some (component)
     *   messages should be destroyed but aren't yet (the ref with message ID 1)
     *   and some do not exist yet (no ref with message ID 6).
     *
     * @returns {mail/static/src/components/message/message.js[]}
     */
    get messageRefs() {
        const refs = this._getRefs();
        const ascOrderedMessageRefs = Object.entries(refs)
            .filter(([refId, ref]) => (
                    // Message refs have message local id as ref id, and message
                    // local ids contain name of model 'mail.message'.
                    refId.includes(this.env.models['mail.message'].modelName) &&
                    // Component that should be destroyed but haven't just yet.
                    ref.message
                )
            )
            .map(([refId, ref]) => ref)
            .sort((ref1, ref2) => (ref1.message.id < ref2.message.id ? -1 : 1));
        if (this.props.order === 'desc') {
            return ascOrderedMessageRefs.reverse();
        }
        return ascOrderedMessageRefs;
    }

    /**
     * @returns {mail.message[]}
     */
    get orderedMessages() {
        const threadCache = this.threadView.threadCache;
        if (this.props.order === 'desc') {
            return [...threadCache.orderedMessages].reverse();
        }
        return threadCache.orderedMessages;
    }

    /**
     * @param {integer} value
     */
    async setScrollTop(value) {
        this._isAutoLoadOnScrollActive = false;
        this.el.scrollTop = value;
        await new Promise(resolve => setTimeout(resolve, 0));
        this._isAutoLoadOnScrollActive = true;
    }

    /**
     * @param {mail.message} prevMessage
     * @param {mail.message} message
     * @returns {boolean}
     */
    shouldMessageBeSquashed(prevMessage, message) {
        if (!this.props.hasSquashCloseMessages) {
            return false;
        }
        if (Math.abs(message.date.diff(prevMessage.date)) > 60000) {
            // more than 1 min. elasped
            return false;
        }
        if (prevMessage.message_type !== 'comment' || message.message_type !== 'comment') {
            return false;
        }
        if (prevMessage.author !== message.author) {
            // from a different author
            return false;
        }
        if (prevMessage.originThread !== message.originThread) {
            return false;
        }
        if (
            prevMessage.moderation_status === 'pending_moderation' ||
            message.moderation_status === 'pending_moderation'
        ) {
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
    }

    /**
     * @returns {mail.thread_view}
     */
    get threadView() {
        return this.env.models['mail.thread_view'].get(this.props.threadViewLocalId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} hint
     */
    async _adjustFromChangeOfThreadCache(hint) {
        const threadCache = this.threadView.threadCache;
        if (!threadCache.isLoaded) {
            return;
        }
        let isProcessed = false;
        if (threadCache.messages.length > 0) {
            if (this.threadView.threadCacheInitialScrollPosition !== undefined) {
                if (this.props.hasScrollAdjust) {
                    if (this.el.scrollHeight === this.threadView.threadCacheInitialScrollHeight) {
                        this.el.scrollTop = this.threadView.threadCacheInitialScrollPosition;
                        isProcessed = true;
                    }
                } else {
                    isProcessed = true;
                }
            } else {
                const lastMessage = threadCache.lastMessage;
                if (this.messageRefFromId(lastMessage.id)) {
                    if (this.props.hasScrollAdjust) {
                        this._scrollToMostRecentMessage();
                    }
                    isProcessed = true;
                }
            }
        } else {
            isProcessed = true;
        }
        if (isProcessed) {
            this.threadView.markComponentHintProcessed(hint);
        }
    }

    /**
     * @private
     * @param {Object} hint
     */
    _adjustFromChatWindowUnfolded(hint) {
        if (this._adjustScrollFromModel()) {
            this.threadView.markComponentHintProcessed(hint);
        }
    }

    /**
     * @private
     * @param {Object} hint
     */
    _adjustFromHomeMenuHidden(hint) {
        if (this._adjustScrollFromModel()) {
            this.threadView.markComponentHintProcessed(hint);
        }
    }

    /**
     * @private
     * @param {Object} hint
     */
    _adjustFromHomeMenuShown(hint) {
        if (this._adjustScrollFromModel()) {
            this.threadView.markComponentHintProcessed(hint);
        }
    }

    /**
     * @private
     * @param {Object} hint
     */
    async _adjustFromMessageReceived(hint) {
        const threadCache = this.threadView.threadCache;
        if (!threadCache.isLoaded) {
            return;
        }
        const { message } = hint.data;
        if (!threadCache.messages.includes(message)) {
            return;
        }
        if (!this.messageRefFromId(message.id)) {
            return;
        }
        if (!this.props.hasScrollAdjust) {
            this.threadView.markComponentHintProcessed(hint);
            return;
        }
        if (!this.threadView.hasAutoScrollOnMessageReceived) {
            this.threadView.markComponentHintProcessed(hint);
            return;
        }
        if (
            this.threadView.lastVisibleMessage &&
            (message.id < this.threadView.lastVisibleMessage.id)
        ) {
            this.threadView.markComponentHintProcessed(hint);
            return;
        }
        await this._scrollToMessage(message.id);
        this.threadView.markComponentHintProcessed(hint);
    }

    /**
     * @private
     * @param {Object} hint
     */
    _adjustFromMoreMessagesLoaded(hint) {
        if (!this._willPatchSnapshot) {
            this.threadView.markComponentHintProcessed(hint);
            return;
        }
        const { scrollHeight, scrollTop } = this._willPatchSnapshot;
        if (this.props.order === 'asc' && this.props.hasScrollAdjust) {
            this.el.scrollTop = this.el.scrollHeight - scrollHeight + scrollTop;
        }
        this.threadView.markComponentHintProcessed(hint);
    }

    /**
     * @private
     * @returns {boolean} whether the adjustment should be considered processed
     */
    _adjustScrollFromModel() {
        if (
            this.threadView.threadCacheInitialScrollPosition !== undefined &&
            this.props.hasScrollAdjust
        ) {
            if (this.el.scrollHeight === this.threadView.threadCacheInitialScrollHeight) {
                this.el.scrollTop = this.threadView.threadCacheInitialScrollPosition;
                return true;
            } else {
                return false;
            }
        }
        return true;
    }

    /**
     * @private
     */
    _checkMostRecentMessageIsVisible() {
        if (!this.threadView) {
            return;
        }
        const thread = this.threadView.thread;
        const threadCache = this.threadView.threadCache;
        const lastMessageIsVisible =
            threadCache &&
            threadCache.messages.length > 0 &&
            this.mostRecentMessageRef &&
            threadCache === thread.mainCache &&
            this.mostRecentMessageRef.isPartiallyVisible();
        if (lastMessageIsVisible) {
            this.threadView.handleVisibleMessage(this.mostRecentMessageRef.message);
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
        const elRect = this.el.getBoundingClientRect();
        const isInvisible = loadMoreRect.top > elRect.bottom || loadMoreRect.bottom < elRect.top;
        return !isInvisible;
    }

    /**
     * @private
     */
    _loadMore() {
        this.threadView.threadCache.loadMoreMessages();
    }

    /**
     * @private
     * @returns {Promise}
     */
    async _scrollToMostRecentMessage() {
        if (!this.mostRecentMessageRef) {
            return;
        }
        this._isAutoLoadOnScrollActive = false;
        await this.mostRecentMessageRef.scrollIntoView();
        if (!this.el) {
            this._isAutoLoadOnScrollActive = true;
            return;
        }
        this.el.scrollTop = this.props.order === 'asc'
            ? this.el.scrollTop + 15
            : this.el.scrollTop - 15;
        this._isAutoLoadOnScrollActive = true;
    }

    /**
     * @param {integer} messageId
     */
    async _scrollToMessage(messageId) {
        const messageRef = this.messageRefFromId(messageId);
        if (!messageRef) {
            return;
        }
        this._isAutoLoadOnScrollActive = false;
        await messageRef.scrollIntoView();
        if (!this.el) {
            this._isAutoLoadOnScrollActive = true;
            return;
        }
        this.el.scrollTop = this.props.order === 'asc'
            ? this.el.scrollTop + 15
            : this.el.scrollTop - 15;
        this._isAutoLoadOnScrollActive = true;
    }

    /**
     * @private
     */
    _update() {
        this.adjustFromComponentHints();
        this._checkMostRecentMessageIsVisible();
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
     * @param {ScrollEvent} ev
     */
    onScroll(ev) {
        if (!this.threadView) {
            return;
        }
        // Clear pending hints to prevent them from potentially overriding the
        // new scroll position.
        for (const hint of this.threadView.componentHintList) {
            this.threadView.markComponentHintProcessed(hint);
        }
        this._onScrollThrottled(ev);
    }

    /**
     * @private
     * @param {ScrollEvent} ev
     */
    _onScrollThrottled(ev) {
        if (!this.el) {
            // could be unmounted in the meantime (due to throttled behavior)
            return;
        }
        if (!this.threadView || !this.threadView.threadViewer) {
            return;
        }
        const scrollTop = this.el.scrollTop;
        this.env.messagingBus.trigger('o-component-message-list-scrolled', {
            scrollTop,
            threadViewer: this.threadView.threadViewer,
        });
        // Margin to compensate for inaccurate scrolling to bottom.
        const margin = 4;
        // Automatically scroll to new received messages only when the list is
        // currently fully scrolled.
        const hasAutoScrollOnMessageReceived = (this.props.order === 'asc')
            ? scrollTop >= this.el.scrollHeight - this.el.clientHeight - margin
            : scrollTop <= margin;
        this.threadView.update({ hasAutoScrollOnMessageReceived });
        this.threadView.threadViewer.saveThreadCacheScrollHeightAsInitial(this.el.scrollHeight);
        this.threadView.threadViewer.saveThreadCacheScrollPositionsAsInitial(scrollTop);
        if (!this._isAutoLoadOnScrollActive) {
            return;
        }
        if (this._isLoadMoreVisible()) {
            this._loadMore();
        }
        this._checkMostRecentMessageIsVisible();
    }

}

Object.assign(MessageList, {
    components,
    defaultProps: {
        hasMessageCheckbox: false,
        hasScrollAdjust: true,
        hasSquashCloseMessages: false,
        haveMessagesMarkAsReadIcon: false,
        haveMessagesReplyIcon: false,
        order: 'asc',
    },
    props: {
        hasMessageCheckbox: Boolean,
        hasSquashCloseMessages: Boolean,
        haveMessagesMarkAsReadIcon: Boolean,
        haveMessagesReplyIcon: Boolean,
        hasScrollAdjust: Boolean,
        order: {
            type: String,
            validate: prop => ['asc', 'desc'].includes(prop),
        },
        selectedMessageLocalId: {
            type: String,
            optional: true,
        },
        threadViewLocalId: String,
    },
    template: 'mail.MessageList',
});

return MessageList;

});
