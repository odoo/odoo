odoo.define('mail.component.MessageList', function (require) {
'use strict';

const Message = require('mail.component.Message');

class MessageList extends owl.store.ConnectedComponent {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this._isAutoLoadOnScrollActive = true;
        this._loadMoreRef = owl.hooks.useRef('loadMore');
        this._onScroll = _.throttle(this._onScroll.bind(this), 100);
        /**
         * Tracked last thread cache rendered. Useful to determine scroll
         * position on patch if it is on the same thread cache or not.
         */
        this._renderedThreadCacheLocalId = null;
        /**
         * Tracked last selected message. Useful to determine when patch comes
         * from a message selection on a given thread cache, so that it
         * auto-scroll to that message.
         */
        this._selectedMessageLocalId = null;
        /**
         * Tracked last thread cache current partner message post counter from
         * the message store. Useful to determine scroll position on patch if
         * this is a patch with new messages on this thread cache, and to
         * determine whether the current partner just recently posted a new
         * message that triggers this patch. Necessary to auto-scroll to this
         * message. Note that a single patch could have current partner newly
         * posted message and other partners new messages, so it should scroll
         * to last message before current partner new message, so that frequent
         * patches with new messages always track the last message.
         */
        this._threadCacheCurrentPartnerMessagePostCounter = null;
        /**
         * Snapshot computed during willPatch, which is used by patched.
         */
        this._willPatchSnapshot = {};
    }

    mounted() {
        this._checkThreadMarkAsRead();
        this._updateTrackedPatchInfo();
        this.trigger('o-message-list-mounted');
    }

    willPatch() {
        const {
            length: l,
            0: firstMessageLocalId,
            [l-1]: lastMessageLocalId,
        } = this.storeProps.messageLocalIds;

        const firstMessageRef = this.firstMessageRef;
        const lastMessageRef = this.lastMessageRef;
        const isPatchedWithNewThreadCache =
            this._renderedThreadCacheLocalId !== this.props.threadCacheLocalId;

        this._willPatchSnapshot = {
            isLastMessageVisible:
                lastMessageRef &&
                lastMessageRef.isBottomVisible({ offset: 10 }),
            isPatchedWithLoadMoreMessages:
                !isPatchedWithNewThreadCache &&
                firstMessageRef &&
                firstMessageRef.props.messageLocalId !== firstMessageLocalId,
            isPatchedWithNewMessages:
                !isPatchedWithNewThreadCache &&
                (
                    (
                        // FIXME:
                        // had messages, has different last message
                        // it assumes it comes from new message, but what if
                        // last message was deleted?
                        // this is important for moderation, in case of message
                        // deletion
                        lastMessageRef &&
                        lastMessageLocalId &&
                        lastMessageRef.props.messageLocalId !== lastMessageLocalId
                    ) ||
                    (
                        // had no messages, now has a last message
                        !lastMessageRef &&
                        lastMessageLocalId
                    )
                ),
            isPatchedWithNewThreadCache,
            scrollHeight: this.el.scrollHeight,
            scrollTop: this.el.scrollTop,
        };
    }

    patched() {
        if (this.storeProps.messages.length === 0) {
            return;
        }
        if (this._willPatchSnapshot.isPatchedWithLoadMoreMessages) {
            this.el.scrollTop =
                this.el.scrollHeight -
                this._willPatchSnapshot.scrollHeight +
                this._willPatchSnapshot.scrollTop;
        } else if (
            this._willPatchSnapshot.isPatchedWithNewThreadCache ||
            (
                this._willPatchSnapshot.isPatchedWithNewMessages &&
                this._willPatchSnapshot.isLastMessageVisible
            )
        ) {
            this.scrollToLastMessage().then(() => this._onScroll());
        } else if (
            this._willPatchSnapshot.isPatchedWithNewMessages &&
            this.storeProps.threadCacheCurrentPartnerMessagePostCounter !==
            this._threadCacheCurrentPartnerMessagePostCounter
        ) {
            this._scrollToLastCurrentPartnerMessage().then(() => this._onScroll());
        } else if (
            !this._selectedMessageLocalId &&
            this._selectedMessageLocalId !== this.props.selectedMessageLocalId &&
            !this.storeProps.isMobile
        ) {
            this._scrollToMessage(this.props.selectedMessageLocalId).then(() => this._onScroll());
        }
        this._checkThreadMarkAsRead();
        this._updateTrackedPatchInfo();
        this._willPatchSnapshot = {};
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @return {mail.component.Message|undefined}
     */
    get firstMessageRef() {
        return this.messageRefs[0];
    }

    /**
     * @return {mail.component.Message|undefined}
     */
    get lastCurrentPartnerMessageRef() {
        const currentPartnerMessageRefs = this.messageRefs.filter(messageRef =>
            messageRef.storeProps.author &&
            messageRef.storeProps.author.id === this.env.session.partner_id);
        let { length: l, [l-1]: lastCurrentPartnerMessageRefs } = currentPartnerMessageRefs;
        return lastCurrentPartnerMessageRefs;
    }

    /**
     * @return {mail.component.Message|undefined}
     */
    get lastMessageRef() {
        let { length: l, [l-1]: lastMessageRef } = this.messageRefs;
        return lastMessageRef;
    }

    /**
     * @return {mail.component.Message[]}
     */
    get messageRefs() {
        return Object.entries(this.__owl__.refs)
            .filter(([refId, ref]) => refId.indexOf('mail.message') !== -1)
            .map(([refId, ref]) => ref)
            .sort((ref1, ref2) => (ref1.storeProps.message.id < ref2.storeProps.message.id ? -1 : 1));
    }
    /**
     * @return {mail.model.Message[]}
     */
    get messages() {
        if (this.props.order === 'desc') {
            return [ ...this.storeProps.messages ].reverse();
        }
        return this.storeProps.messages;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {mail.store.model.Message} message
     * @return {string}
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
     * @return {integer}
     */
    getScrollTop() {
        return this.el.scrollTop;
    }

    /**
     * @return {boolean}
     */
    hasMessages() {
        return this.storeProps.messages && this.storeProps.messages.length > 0;
    }

    /**
     * @return {Promise}
     */
    async scrollToLastMessage() {
        this._isAutoLoadOnScrollActive = false;
        await this.lastMessageRef.scrollIntoView();
        if (!this.el) {
            return;
        }
        this.el.scrollTop += 15;
        this._isAutoLoadOnScrollActive = true;
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
     * @param {mail.store.model.Message} prevMessage
     * @param {mail.store.model.Message} message
     * @return {boolean}
     */
    shouldMessageBeSquashed(prevMessage, message) {
        if (!this.props.hasSquashCloseMessages) {
            return false;
        }
        const prevDate = prevMessage.date;
        const date = message.date;
        if (Math.abs(date.diff(prevDate)) > 60000) {
            // more than 1 min. elasped
            return false;
        }
        if (prevMessage.message_type !== 'comment' || message.message_type !== 'comment') {
            return false;
        }
        if (prevMessage.authorLocalId !== message.authorLocalId) {
            // from a different author
            return false;
        }
        if (prevMessage.originThreadLocalId !== message.originThreadLocalId) {
            return false;
        }
        const prevOriginThread = this.env.store.state.threads[prevMessage.originThreadLocalId];
        const originThread = this.env.store.state.threads[message.originThreadLocalId];
        if (
            prevOriginThread &&
            originThread &&
            prevOriginThread._model === originThread._model &&
            originThread._model !== 'mail.channel' &&
            prevOriginThread.id !== originThread.id
        ) {
            // messages linked to different document thread
            return false;
        }
        return true;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _checkThreadMarkAsRead() {
        if (this.storeProps.messages.length === 0) {
            return;
        }
        if (
            !this.props.domain.length &&
            this.lastMessageRef.isPartiallyVisible()
        ) {
            this.dispatch('markThreadAsSeen', this.props.threadLocalId);
        }
    }

    /**
     * @private
     * @return {boolean}
     */
    _isLoadMoreVisible() {
        const loadMore = this._loadMoreRef.el;
        if (!loadMore) {
            return false;
        }
        const loadMoreRect = loadMore.getBoundingClientRect();
        const elRect = this.el.getBoundingClientRect();
        // intersection with 15px offset
        return (
            loadMoreRect.top < elRect.bottom + 15 &&
            elRect.top < loadMoreRect.bottom + 15
        );
    }

    /**
     * @private
     */
    _loadMore() {
        this.dispatch('loadMoreMessagesOnThread', this.props.threadLocalId, {
            searchDomain: this.props.domain,
        });
    }

    /**
     * @private
     * @param {string} messageLocalId
     */
    async _scrollToMessage(messageLocalId) {
        this._isAutoLoadOnScrollActive = false;
        await this.__owl__.refs[messageLocalId].scrollIntoView({
            block:'nearest',
        });
        if (!this.el) {
            return;
        }
        this.el.scrollTop += 15;
        this._isAutoLoadOnScrollActive = true;
    }

    /**
     * @private
     */
    async _scrollToLastCurrentPartnerMessage() {
        this._isAutoLoadOnScrollActive = false;
        await this.lastCurrentPartnerMessageRef.scrollIntoView();
        if (!this.el) {
            return;
        }
        this.el.scrollTop += 15;
        this._isAutoLoadOnScrollActive = true;
    }

    /**
     * @private
     */
    _updateTrackedPatchInfo() {
        this._renderedThreadCacheLocalId = this.props.threadCacheLocalId;
        this._selectedMessageLocalId = this.props.selectedMessageLocalId;
        this._threadCacheCurrentPartnerMessagePostCounter =
            this.storeProps.threadCacheCurrentPartnerMessagePostCounter;
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
        if (!this._isAutoLoadOnScrollActive) {
            return;
        }
        if (this._isLoadMoreVisible()) {
            this._loadMore();
        }
        this._checkThreadMarkAsRead();
    }
}

MessageList.components = {
    Message,
};

MessageList.defaultProps = {
    domain: [],
    hasSquashCloseMessages: false,
    haveMessagesAuthorRedirect: false,
    haveMessagesMarkAsReadIcon: false,
    haveMessagesReplyIcon: false,
    order: 'asc',
};

/**
 * @param {Object} state
 * @param {Object} ownProps
 * @param {string} ownProps.threadCacheLocalId
 * @param {string} ownProps.threadLocalId
 * @return {Object}
 */
MessageList.mapStoreToProps = function (state, ownProps) {
    const threadCache = state.threadCaches[ownProps.threadCacheLocalId];
    return {
        isMobile: state.isMobile,
        messageLocalIds: threadCache.messageLocalIds,
        messages: threadCache.messageLocalIds.map(localId => state.messages[localId]),
        thread: state.threads[ownProps.threadLocalId],
        threadCache,
        threadCacheCurrentPartnerMessagePostCounter: threadCache.currentPartnerMessagePostCounter,
    };
};

MessageList.props = {
    domain: Array,
    hasSquashCloseMessages: Boolean,
    haveMessagesAuthorRedirect: Boolean,
    haveMessagesMarkAsReadIcon: Boolean,
    haveMessagesReplyIcon: Boolean,
    order: String, // ['asc', 'desc']
    selectedMessageLocalId: {
        type: String,
        optional: true,
    },
    threadCacheLocalId: String,
    threadLocalId: String,
};

MessageList.template = 'mail.component.MessageList';

return MessageList;

});
