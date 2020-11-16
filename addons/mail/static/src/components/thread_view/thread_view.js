odoo.define('mail/static/src/components/thread_view/thread_view.js', function (require) {
'use strict';

const components = {
    Composer: require('mail/static/src/components/composer/composer.js'),
    MessageList: require('mail/static/src/components/message_list/message_list.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');
const useUpdate = require('mail/static/src/component_hooks/use_update/use_update.js');

const { Component } = owl;
const { useRef } = owl.hooks;

class ThreadView extends Component {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        useStore((...args) => this._useStoreSelector(...args));
        useUpdate({
            func: () => this._update(),
            priority: 100, // must be executed after composer height adjust
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
     * Get the scroll height in the message list.
     *
     * @returns {integer|undefined}
     */
    getScrollHeight() {
        if (!this._messageListRef.comp) {
            return undefined;
        }
        return this._messageListRef.comp.getScrollHeight();
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
     * @private
     * @param {MouseEvent} ev
     */
    onScroll(ev) {
        if (!this._messageListRef.comp) {
            return;
        }
        this._messageListRef.comp.onScroll(ev);
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
        const threadView = this.env.models['mail.thread_view'].get(props.threadViewLocalId);
        const thread = threadView ? threadView.thread : undefined;
        const threadCache = threadView ? threadView.threadCache : undefined;
        return {
            isDeviceMobile: this.env.messaging.device.isMobile,
            thread: thread ? thread.__state : undefined,
            threadCache: threadCache ? threadCache.__state : undefined,
            threadView: threadView ? threadView.__state : undefined,
        };
    }

}

Object.assign(ThreadView, {
    components,
    defaultProps: {
        composerAttachmentsDetailsMode: 'auto',
        hasComposer: false,
        hasMessageCheckbox: false,
        hasSquashCloseMessages: false,
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
        haveMessagesMarkAsReadIcon: Boolean,
        haveMessagesReplyIcon: Boolean,
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
        threadViewLocalId: String,
    },
    template: 'mail.ThreadView',
});

return ThreadView;

});
