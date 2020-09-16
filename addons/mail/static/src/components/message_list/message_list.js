odoo.define('mail/static/src/components/message_list/message_list.js', function (require) {
'use strict';

const components = {
    Message: require('mail/static/src/components/message/message.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');
const useRefs = require('mail/static/src/component_hooks/use_refs/use_refs.js');

const { Component } = owl;
const { useRef } = owl.hooks;

class MessageList extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
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
     * is rendered. To make this simpler, this is done when <ThreadView/>
     * component is patched. This is acceptable when <ThreadView/> has a
     * fixed height, which is the case for the moment.
     */
    async adjustFromComponentHints() {
        if (!this.threadView) {
            return;
        }
        for (const hint of this.threadView.__mfield_componentHintList(this)) {
            switch (hint.type) {
                case 'change-of-thread-cache':
                    this._adjustFromChangeOfThreadCache(hint);
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
            }
        }
        this._willPatchSnapshot = undefined;
    }

    /**
     * @param {mail.message} message
     * @returns {string}
     */
    getDateDay(message) {
        const date = message.__mfield_date(this).format('YYYY-MM-DD');
        if (date === moment().format('YYYY-MM-DD')) {
            return this.env._t("Today");
        } else if (
            date === moment()
                .subtract(1, 'days')
                .format('YYYY-MM-DD')
        ) {
            return this.env._t("Yesterday");
        }
        return message.__mfield_date(this).format('LL');
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
        return this.messageRefs.find(ref => ref.message.__mfield_id(this) === messageId);
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
            .sort((ref1, ref2) => (
                ref1.message.__mfield_id(this) < ref2.message.__mfield_id(this) ? -1 : 1)
            );
        if (this.props.order === 'desc') {
            return ascOrderedMessageRefs.reverse();
        }
        return ascOrderedMessageRefs;
    }

    /**
     * @returns {mail.message[]}
     */
    get orderedMessages() {
        const threadCache = this.threadView.__mfield_threadCache(this);
        if (this.props.order === 'desc') {
            return [...threadCache.__mfield_orderedMessages(this)].reverse();
        }
        return threadCache.__mfield_orderedMessages(this);
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
        if (Math.abs(message.__mfield_date(this).diff(prevMessage.__mfield_date(this))) > 60000) {
            // more than 1 min. elasped
            return false;
        }
        if (
            prevMessage.__mfield_message_type(this) !== 'comment' ||
            message.__mfield_message_type(this) !== 'comment'
        ) {
            return false;
        }
        if (prevMessage.__mfield_author(this) !== message.__mfield_author(this)) {
            // from a different author
            return false;
        }
        if (prevMessage.__mfield_originThread(this) !== message.__mfield_originThread(this)) {
            return false;
        }
        if (
            prevMessage.__mfield_moderation_status(this) === 'pending_moderation' ||
            message.__mfield_moderation_status(this) === 'pending_moderation'
        ) {
            return false;
        }
        if (
            prevMessage.__mfield_notifications(this).length > 0 ||
            message.__mfield_notifications(this).length > 0
        ) {
            // visual about notifications is restricted to non-squashed messages
            return false;
        }
        const prevOriginThread = prevMessage.__mfield_originThread(this);
        const originThread = message.__mfield_originThread(this);
        if (
            prevOriginThread &&
            originThread &&
            prevOriginThread.__mfield_model(this) === originThread.__mfield_model(this) &&
            originThread.__mfield_model(this) !== 'mail.channel' &&
            prevOriginThread.__mfield_id(this) !== originThread.__mfield_id(this)
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
        const threadCache = this.threadView.__mfield_threadCache(this);
        if (!threadCache.__mfield_isLoaded(this)) {
            return;
        }
        let isProcessed = false;
        if (threadCache.__mfield_messages(this).length > 0) {
            if (this.threadView.__mfield_threadCacheInitialScrollPosition(this) !== undefined) {
                if (this.props.hasScrollAdjust) {
                    this.el.scrollTop = this.threadView.__mfield_threadCacheInitialScrollPosition(this);
                }
                isProcessed = true;
            } else {
                const lastMessage = threadCache.__mfield_lastMessage(this);
                if (this.messageRefFromId(lastMessage.__mfield_id(this))) {
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
            this.env.messagingBus.trigger('o-component-message-list-thread-cache-changed', {
                threadViewer: this.threadView.__mfield_threadViewer(this),
            });
            this.threadView.markComponentHintProcessed(hint);
        }
    }

    /**
     * @private
     * @param {Object} hint
     */
    _adjustFromChatWindowUnfolded(hint) {
        this._adjustScrollFromModel();
        this.threadView.markComponentHintProcessed(hint);
    }

    /**
     * @private
     * @param {Object} hint
     * @param {Object} hint.data
     * @param {integer} hint.data.messageId
     */
    async _adjustFromCurrentPartnerJustPostedMessage(hint) {
        const threadCache = this.threadView.__mfield_threadCache(this);
        if (threadCache.__mfield_isLoaded(this) && hint.data) {
            const { messageId } = hint.data;
            const threadCacheMessageIds = threadCache.__mfield_messages(this).map(message => message.__mfield_id(this));
            if (threadCacheMessageIds.includes(messageId) && this.messageRefFromId(messageId)) {
                if (this.props.hasScrollAdjust) {
                    await this._scrollToMessage(messageId);
                }
                this.threadView.markComponentHintProcessed(hint);
            }
        }
    }

    /**
     * @private
     * @param {Object} hint
     */
    _adjustFromHomeMenuHidden(hint) {
        this._adjustScrollFromModel();
        this.threadView.markComponentHintProcessed(hint);
    }

    /**
     * @private
     * @param {Object} hint
     */
    _adjustFromHomeMenuShown(hint) {
        this._adjustScrollFromModel();
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
        this.env.messagingBus.trigger('o-component-message-list-more-messages-loaded', {
            threadViewer: this.threadView.__mfield_threadViewer(this),
        });
        this.threadView.markComponentHintProcessed(hint);
    }

    /**
     * @private
     */
    _adjustScrollFromModel() {
        if (
            this.threadView.__mfield_threadCacheInitialScrollPosition(this) !== undefined &&
            this.props.hasScrollAdjust
        ) {
            this.el.scrollTop = this.threadView.__mfield_threadCacheInitialScrollPosition(this);
        }
    }

    /**
     * @private
     */
    _checkMostRecentMessageIsVisible() {
        if (!this.threadView) {
            return;
        }
        const thread = this.threadView.__mfield_thread(this);
        const threadCache = this.threadView.__mfield_threadCache(this);
        const lastMessageIsVisible =
            threadCache &&
            threadCache.__mfield_messages(this).length > 0 &&
            this.mostRecentMessageRef &&
            threadCache === thread.__mfield_mainCache(this) &&
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
        this.threadView.__mfield_threadCache(this).loadMoreMessages();
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
        if (!this.threadView || !this.threadView.__mfield_threadViewer(this)) {
            return;
        }
        const scrollTop = this.el.scrollTop;
        this.env.messagingBus.trigger('o-component-message-list-scrolled', {
            scrollTop,
            threadViewer: this.threadView.__mfield_threadViewer(this),
        });
        this.threadView.__mfield_threadViewer(this).saveThreadCacheScrollPositionsAsInitial(scrollTop);
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
