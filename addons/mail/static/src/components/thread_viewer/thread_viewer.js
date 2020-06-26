odoo.define('mail/static/src/components/thread_viewer/thread_viewer.js', function (require) {
'use strict';

const components = {
    Composer: require('mail/static/src/components/composer/composer.js'),
    MessageList: require('mail/static/src/components/message_list/message_list.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;
const { useRef } = owl.hooks;

class ThreadViewer extends Component {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        useStore((...args) => this._useStoreSelector(...args));
        /**
         * Reference of the composer. Useful to set focus on composer when
         * thread has the focus.
         */
        this._composerRef = useRef('composer');
        /**
         * Reference of the message list. Useful to determine scroll positions.
         */
        this._messageListRef = useRef('messageList');
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
     * @returns {integer|undefined}
     */
    getScrollTop() {
        if (!this._messageListRef.comp) {
            return undefined;
        }
        return this._messageListRef.comp.getScrollTop();
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
     * Called when thread component is mounted or patched.
     *
     * @private
     */
    _update() {
        const messageList = this._messageListRef.comp;
        this.trigger('o-rendered');
        /**
         * Control panel may offset scrolling position of message list due to
         * height of buttons. To prevent this, control panel re-render is
         * triggered before message list. Correct way should be to adjust
         * scroll positions after everything has been rendered, but OWL doesn't
         * have such an API for the moment.
         */
        if (messageList) {
            messageList.adjustFromComponentHints();
        }
    }

    /**
     * Returns data selected from the store.
     *
     * @private
     * @param {Object} props
     * @returns {Object}
     */
    _useStoreSelector(props) {
        const threadViewer = this.env.models['mail.thread_viewer'].get(props.threadViewerLocalId);
        const thread = threadViewer ? threadViewer.thread : undefined;
        const threadCache = threadViewer ? threadViewer.threadCache : undefined;
        return {
            isDeviceMobile: this.env.messaging.device.isMobile,
            thread: thread ? thread.__state : undefined,
            threadCache: threadCache ? threadCache.__state : undefined,
            threadViewer: threadViewer ? threadViewer.__state : undefined,
        };
    }

}

Object.assign(ThreadViewer, {
    components,
    defaultProps: {
        composerAttachmentsDetailsMode: 'auto',
        hasComposer: false,
        hasMessageCheckbox: false,
        hasSquashCloseMessages: false,
        haveMessagesAuthorRedirect: false,
        haveMessagesMarkAsReadIcon: false,
        haveMessagesReplyIcon: false,
        order: 'asc',
        showComposerAttachmentsExtensions: true,
        showComposerAttachmentsFilenames: true,
    },
    props: {
        composerAttachmentsDetailsMode: {
            type: String,
            validate: prop => ['auto', 'card', 'hover', 'none'].includes(prop),
        },
        hasComposer: Boolean,
        hasComposerCurrentPartnerAvatar: {
            type: Boolean,
            optional: true,
        },
        hasComposerSendButton: {
            type: Boolean,
            optional: true,
        },
        /**
         * If set, determines whether the composer should display status of
         * members typing on related thread. When this prop is not provided,
         * it defaults to composer component default value.
         */
        hasComposerThreadTyping: {
            type: Boolean,
            optional: true,
        },
        hasMessageCheckbox: Boolean,
        hasScrollAdjust: {
            type: Boolean,
            optional: true,
        },
        hasSquashCloseMessages: Boolean,
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
        order: {
            type: String,
            validate: prop => ['asc', 'desc'].includes(prop),
        },
        selectedMessageLocalId: {
            type: String,
            optional: true,
        },
        showComposerAttachmentsExtensions: Boolean,
        showComposerAttachmentsFilenames: Boolean,
        threadViewerLocalId: String,
    },
    template: 'mail.ThreadViewer',
});

return ThreadViewer;

});
