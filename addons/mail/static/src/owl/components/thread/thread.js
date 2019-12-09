odoo.define('mail.component.Thread', function (require) {
'use strict';

const Composer = require('mail.component.Composer');
const MessageList = require('mail.component.MessageList');

const { Component } = owl;
const { useDispatch, useRef, useStore } = owl.hooks;

class Thread extends Component {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        /**
         * Unique id of this thread component instance.
         * Useful to provide a unique id to composer instance, which is useful
         * to manage relations between composers and attachments.
         * AKU TODO: maybe composer itself can compute it???
         */
        this.id = _.uniqueId('o_thread_');
        this.storeDispatch = useDispatch();
        this.storeProps = useStore((state, props) => {
            const thread = state.threads[props.threadLocalId];
            const threadCacheLocalId = thread
                ? thread.cacheLocalIds[JSON.stringify(props.domain || [])]
                : undefined;
            const threadCache = threadCacheLocalId
                ? state.threadCaches[threadCacheLocalId]
                : undefined;
            return {
                isMobile: state.isMobile,
                thread,
                threadCache,
                threadCacheLocalId,
            };
        });
        /**
         * Reference of the composer. Useful to set focus on composer when
         * thread has the focus.
         */
        this._composerRef = useRef('composer');
        /**
         * Reference of the message list. Useful to determine scroll positions.
         */
        this._messageListRef = useRef('messageList');

        /**
         * Last rendered thread cache. Useful to determine a change of thread
         * cache, which is useful to set initial scroll position of message
         * list.
         */
        this._lastRenderedThreadCacheLocalId = undefined;
        /**
         * Determine whether there is a change of thread cache happening.
         * This is useful to set initial scroll position of message. Note that
         * there may be a change of thread cache, but the cache is not yet
         * loaded, hence setting the initial scroll position of message list
         * may have to wait for several patches.
         */
        this._isChangeOfThreadCache = false;
    }

    mounted() {
        this._update();
    }

    patched() {
        this._update();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Focus the thread. If it has a composer, focus it.
     */
    focus() {
        if (!this._composerRef.comp) {
            return;
        }
        this._composerRef.comp.focus();
    }

    /**
     * Focusout the thread.
     */
    focusout() {
        if (!this._composerRef.comp) {
            return;
        }
        this._composerRef.comp.focusout();
    }

    /**
     * Get the scroll position in the message list.
     *
     * @return {integer|undefined}
     */
    getScrollTop() {
        if (!this._messageListRef.comp) {
            return undefined;
        }
        return this._messageListRef.comp.getScrollTop();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Load the thread cache, i.e. the thread at given domain for the messages.
     *
     * @private
     */
    _loadThreadCache() {
        this.storeDispatch('loadThreadCache', this.props.threadLocalId, {
            searchDomain: this.props.domain,
        });
    }

    /**
     * Set the scroll position of message list.
     *
     * @private
     */
    async _setMessageListInitialScroll() {
        const messageList = this._messageListRef.comp;
        if (this.props.messageListInitialScrollTop !== undefined) {
            await messageList.setScrollTop(this.props.messageListInitialScrollTop);
        } else if (messageList.hasMessages()) {
            await messageList.scrollToLastMessage();
        }
    }

    /**
     * Called when thread component is mounted or patched.
     *
     * @private
     */
    _update() {
        // TODO SEB move this outside mounted (in constructor + will update props)
        if (!this.storeProps.threadCache || (!this.storeProps.threadCache.isLoaded && !this.storeProps.threadCache.isLoading)) {
            this._loadThreadCache();
        }
        if (this._lastRenderedThreadCacheLocalId !== this.storeProps.threadCacheLocalId) {
            this._isChangeOfThreadCache = true;
        }
        if (this._isChangeOfThreadCache && this._messageListRef.comp) {
            this._setMessageListInitialScroll();
            this._isChangeOfThreadCache = false;
        } else if (this._messageListRef.comp) {
            this._messageListRef.comp.updateScroll();
        }
        this._lastRenderedThreadCacheLocalId = this.storeProps.threadCacheLocalId;
        this.trigger('o-rendered');
    }
}

Thread.components = {
    Composer,
    MessageList,
};

Thread.defaultProps = {
    composerAttachmentsDetailsMode: 'auto',
    domain: [],
    hasComposer: false,
    hasSquashCloseMessages: false,
    haveMessagesAuthorRedirect: false,
    haveMessagesMarkAsReadIcon: false,
    haveMessagesReplyIcon: false,
    order: 'asc',
    showComposerAttachmentsExtensions: true,
    showComposerAttachmentsFilenames: true,
};

Thread.props = {
    composerAttachmentsDetailsMode: {
        type: String, //['auto', 'card', 'hover', 'none']
    },
    domain: {
        type: Array,
    },
    hasComposer: {
        type: Boolean,
    },
    hasComposerCurrentPartnerAvatar: {
        type: Boolean,
        optional: true,
    },
    hasComposerSendButton: {
        type: Boolean,
        optional: true,
    },
    hasSquashCloseMessages: {
        type: Boolean,
    },
    haveMessagesAuthorRedirect: {
        type: Boolean,
    },
    haveMessagesMarkAsReadIcon: {
        type: Boolean,
    },
    haveMessagesReplyIcon: {
        type: Boolean,
    },
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
    order: {
        type: String, // ['asc', 'desc']
    },
    selectedMessageLocalId: {
        type: String,
        optional: true,
    },
    showComposerAttachmentsExtensions: {
        type: Boolean,
    },
    showComposerAttachmentsFilenames: {
        type: Boolean,
    },
    threadLocalId: String,
};

Thread.template = 'mail.component.Thread';

return Thread;

});
