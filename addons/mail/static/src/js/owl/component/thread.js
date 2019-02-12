odoo.define('mail.component.Thread', function (require) {
'use strict';

const Composer = require('mail.component.Composer');
const MessageList = require('mail.component.MessageList');

class Thread extends owl.store.ConnectedComponent {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.id = _.uniqueId('o_thread_');
        this._composerRef = owl.hooks.useRef('composer');
        /**
         * Track when message list has been mounted. Message list should notify
         * by means of `o-message-list-mounted` custom event, so that next
         * `mounted()` or `patched()` call set the scroll position of message
         * list. @see messageListInitialScrollTop prop definitions.
         */
        this._isMessageListJustMounted = false;
        this._messageListRef = owl.hooks.useRef('messageList');
    }

    mounted() {
        if (
            !this.storeProps.threadCache ||
            (
                !this.storeProps.threadCache.isLoaded &&
                !this.storeProps.threadCache.isLoading
            )
        ) {
            this._loadThreadCache();
        }
        if (this._isMessageListJustMounted) {
            this._isMessageListJustMounted = false;
            this._handleMessageListScrollOnMount();
        }
        this.trigger('o-rendered');
    }

    patched() {
        if (
            !this.storeProps.threadCache ||
            (
                !this.storeProps.threadCache.isLoaded &&
                !this.storeProps.threadCache.isLoading
            )
        ) {
            this._loadThreadCache();
        }
        if (this._isMessageListJustMounted) {
            this._isMessageListJustMounted = false;
            this._handleMessageListScrollOnMount();
        }
        this.trigger('o-rendered');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    focus() {
        if (!this._composerRef.comp) {
            return;
        }
        this._composerRef.comp.focus();
    }

    focusout() {
        if (!this._composerRef.comp) {
            return;
        }
        this._composerRef.comp.focusout();
    }

    /**
     * Get the state of the composer. This is useful to backup thread state on
     * re-mount.
     *
     * @return {Object|undefined}
     */
    getComposerState() {
        if (!this.props.hasComposer) {
            return;
        }
        return this._composerRef.comp.getState();
    }

    /**
     * @return {integer|undefined}
     */
    getScrollTop() {
        if (
            !this.storeProps.threadCache ||
            !this.storeProps.threadCache.isLoaded
        ) {
            return undefined;
        }
        return this._messageListRef.comp.getScrollTop();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Handle initial scroll value for message list subcomponent.
     * We need to this within thread as the scroll position for message list
     * can be affected by the composer component.
     *
     * @private
     */
    async _handleMessageListScrollOnMount() {
        const messageList = this._messageListRef.comp;
        if (this.props.messageListInitialScrollTop !== undefined) {
            await messageList.setScrollTop(this.props.messageListInitialScrollTop);
        } else if (messageList.hasMessages()) {
            await messageList.scrollToLastMessage();
        }
    }

    /**
     * @private
     */
    _loadThreadCache() {
        this.dispatch('loadThreadCache', this.props.threadLocalId, {
            searchDomain: this.props.domain,
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onMessageListMounted(ev) {
        this._isMessageListJustMounted = true;
    }
}

Thread.components = {
    Composer,
    MessageList,
};

Thread.defaultProps = {
    domain: [],
    hasComposer: false,
    haveMessagesAuthorRedirect: false,
    haveMessagesMarkAsReadIcon: false,
    haveMessagesReplyIcon: false,
    hasSquashCloseMessages: false,
    order: 'asc',
};

/**
 * @param {Object} state
 * @param {Object} ownProps
 * @param {Array} [ownProps.domain=[]]
 * @param {string} ownProps.threadLocalId
 * @return {Object}
 */
Thread.mapStoreToProps = function (state, ownProps) {
    const thread = state.threads[ownProps.threadLocalId];
    const threadCacheLocalId = thread
        ? thread.cacheLocalIds[JSON.stringify(ownProps.domain || [])]
        : undefined;
    const threadCache = threadCacheLocalId
        ? state.threadCaches[threadCacheLocalId]
        : undefined;
    return {
        isMobile: state.isMobile,
        threadCache,
        threadCacheLocalId,
    };
};

Thread.props = {
    areComposerAttachmentsEditable: {
        type: Boolean,
        optional: true,
    },
    composerAttachmentLayout: {
        type: String,
        optional: true,
    },
    composerInitialAttachmentLocalIds: {
        type: Array,
        element: String,
        optional: true,
    },
    composerInitialTextInputHtmlContent: {
        type: String,
        optional: true,
    },
    domain: Array,
    hasComposer: Boolean,
    hasComposerCurrentPartnerAvatar: {
        type: Boolean,
        optional: true,
    },
    hasComposerSendButton: {
        type: Boolean,
        optional: true,
    },
    hasSquashCloseMessages: Boolean,
    haveComposerAttachmentsLabelForCardLayout: {
        type: Boolean,
        optional: true,
    },
    haveMessagesAuthorRedirect: Boolean,
    haveMessagesMarkAsReadIcon: Boolean,
    haveMessagesReplyIcon: Boolean,
    /**
     * Set the initial scroll position of message list on mount. Note that
     * this prop is not directly passed to message list as props because
     * it may compute scroll top without composer, and then composer may alter
     * them on mount. To solve this issue, thread handles setting initial scroll
     * positions, so that this is always done after composer has been mounted.
     * (child `mounted()` are called before parent `mounted()`)
     */
    messageListInitialScrollTop: {
        type: Number,
        optional: true
    },
    order: String, // ['asc', 'desc']
    selectedMessageLocalId: {
        type: String,
        optional: true,
    },
    threadLocalId: String,
};

Thread.template = 'mail.component.Thread';

return Thread;

});
