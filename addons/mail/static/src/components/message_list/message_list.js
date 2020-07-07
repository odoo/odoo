odoo.define('mail/static/src/components/message_list/message_list.js', function (require) {
'use strict';

const components = {
    Message: require('mail/static/src/components/message/message.js'),
};
const useRefs = require('mail/static/src/component_hooks/use_refs/use_refs.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;
const { useRef } = owl.hooks;

class MessageList extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const threadViewer = this.env.models['mail.thread_viewer'].get(props.threadViewerLocalId);
            const thread = threadViewer ? threadViewer.thread : undefined;
            const threadCache = threadViewer ? threadViewer.threadCache : undefined;
            return {
                isDeviceMobile: this.env.messaging.device.isMobile,
                messages: threadCache
                    ? threadCache.orderedMessages.map(message => message.__state)
                    : [],
                thread: thread ? thread.__state : undefined,
                threadCache: threadCache ? threadCache.__state : undefined,
                threadViewer: threadViewer ? threadViewer.__state : undefined,
            };
        }, {
            compareDepth: {
                messages: 1,
            },
        });
        this._getRefs = useRefs();
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
         * Tracked last thread cache rendered. Useful to determine scroll
         * position on patch if it is on the same thread cache or not.
         */
        this._renderedThreadCache = null;
        /**
         * Tracked last selected message. Useful to determine when patch comes
         * from a message selection on a given thread cache, so that it
         * auto-scroll to that message.
         */
        this._selectedMessage = null;
        /**
         * Snapshot computed during willPatch, which is used by patched.
         */
        this._willPatchSnapshot = undefined;
        this._onScroll = _.throttle(this._onScroll.bind(this), 100);
    }

    mounted() {
        this._update();
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

    patched() {
        this._update();
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
     * is rendered. To make this simpler, this is done when <ThreadViewer/>
     * component is patched. This is acceptable when <ThreadViewer/> has a
     * fixed height, which is the case for the moment.
     */
    async adjustFromComponentHints() {
        for (const hint of this.threadViewer.componentHintList) {
            switch (hint.type) {
                case 'change-of-thread-cache':
                    this._adjustFromChangeOfThreadCache(hint);
                    break;
                case 'chat-window-unfolded':
                    this._adjustFromChatWindowUnfolded(hint);
                    break;
                case 'current-partner-just-posted-message':
                    this._adjustFromCurrentPartnerJustPostedMessage(hint);
                    break;
                case 'home-menu-hidden':
                    this._adjustFromHomeMenuHidden(hint);
                    break;
                case 'home-menu-shown':
                    this._adjustFromHomeMenuShown(hint);
                    break;
                case 'more-messages-loaded':
                    this._adjustFromMoreMessagesLoaded(hint);
                    break;
                default:
                    this.threadViewer.markComponentHintProcessed(hint);
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
        const threadCache = this.threadViewer.threadCache;
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
     * @returns {mail.thread_viewer}
     */
    get threadViewer() {
        return this.env.models['mail.thread_viewer'].get(this.props.threadViewerLocalId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} hint
     */
    async _adjustFromChangeOfThreadCache(hint) {
        const threadCache = this.threadViewer.threadCache;
        if (!threadCache.isLoaded) {
            return;
        }
        let isProcessed = false;
        if (threadCache.messages.length > 0) {
            if (this.threadViewer.threadCacheInitialScrollPosition !== undefined) {
                if (this.props.hasScrollAdjust) {
                    this.el.scrollTop = this.threadViewer.threadCacheInitialScrollPosition;
                }
                isProcessed = true;
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
            this.threadViewer.markComponentHintProcessed(hint);
        }
    }

    /**
     * @private
     * @param {Object} hint
     */
    _adjustFromChatWindowUnfolded(hint) {
        this._adjustScrollFromModel();
        this.threadViewer.markComponentHintProcessed(hint);
    }

    /**
     * @private
     * @param {Object} hint
     * @param {Object} hint.data
     * @param {integer} hint.data.messageId
     */
    async _adjustFromCurrentPartnerJustPostedMessage(hint) {
        const threadCache = this.threadViewer.threadCache;
        const { messageId } = hint.data;
        if (threadCache.isLoaded) {
            const threadCacheMessageIds = threadCache.messages.map(message => message.id);
            if (threadCacheMessageIds.includes(messageId) && this.messageRefFromId(messageId)) {
                if (this.props.hasScrollAdjust) {
                    await this._scrollToMessage(messageId);
                }
                this.threadViewer.markComponentHintProcessed(hint);
            }
        }
    }

    /**
     * @private
     * @param {Object} hint
     */
    _adjustFromHomeMenuHidden(hint) {
        this._adjustScrollFromModel();
        this.threadViewer.markComponentHintProcessed(hint);
    }

    /**
     * @private
     * @param {Object} hint
     */
    _adjustFromHomeMenuShown(hint) {
        this._adjustScrollFromModel();
        this.threadViewer.markComponentHintProcessed(hint);
    }

    /**
     * @private
     * @param {Object} hint
     */
    _adjustFromMoreMessagesLoaded(hint) {
        if (!this._willPatchSnapshot) {
            this.threadViewer.markComponentHintProcessed(hint);
            return;
        }
        const { scrollHeight, scrollTop } = this._willPatchSnapshot;
        if (this.props.order === 'asc' && this.props.hasScrollAdjust) {
            this.el.scrollTop = this.el.scrollHeight - scrollHeight + scrollTop;
        }
        this.threadViewer.markComponentHintProcessed(hint);
    }

    /**
     * @private
     */
    _adjustScrollFromModel() {
        if (
            this.threadViewer.threadCacheInitialScrollPosition !== undefined &&
            this.props.hasScrollAdjust
        ) {
            this.el.scrollTop = this.threadViewer.threadCacheInitialScrollPosition;
        }
    }

    /**
     * @private
     */
    _checkMostRecentMessageIsVisible() {
        const thread = this.threadViewer.thread;
        const threadCache = this.threadViewer.threadCache;
        const lastMessageIsVisible =
            threadCache &&
            threadCache.messages.length > 0 &&
            this.mostRecentMessageRef &&
            threadCache === thread.mainCache &&
            this.mostRecentMessageRef.isPartiallyVisible();
        if (lastMessageIsVisible) {
            this.threadViewer.handleVisibleMessage(this.mostRecentMessageRef.message);
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
        this.threadViewer.threadCache.loadMoreMessages();
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
    _onScroll(ev) {
        if (!this.el) {
            // could be unmounted in the meantime (due to throttled behavior)
            return;
        }
        this.threadViewer.saveThreadCacheScrollPositionsAsInitial(this.el.scrollTop);
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
        haveMessagesAuthorRedirect: false,
        haveMessagesMarkAsReadIcon: false,
        haveMessagesReplyIcon: false,
        order: 'asc',
    },
    props: {
        hasMessageCheckbox: Boolean,
        hasSquashCloseMessages: Boolean,
        haveMessagesAuthorRedirect: Boolean,
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
        threadViewerLocalId: String,
    },
    template: 'mail.MessageList',
});

return MessageList;

});
