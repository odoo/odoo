odoo.define('mail/static/src/components/thread_view/thread_view.js', function (require) {
'use strict';

const components = {
    Composer: require('mail/static/src/components/composer/composer.js'),
    MessageList: require('mail/static/src/components/message_list/message_list.js'),
};
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
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
        useShouldUpdateBasedOnProps();
        useStore((...args) => this._useStoreSelector(...args), {
            compareDepth: {
                threadTextInputSendShortcuts: 1,
            },
        });
        useUpdate({ func: () => this._update() });
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
        this.trigger('o-rendered');
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
        const correspondent = thread && thread.correspondent;
        return {
            composer: thread && thread.composer,
            correspondentId: correspondent && correspondent.id,
            isDeviceMobile: this.env.messaging.device.isMobile,
            thread,
            threadCacheIsLoaded: threadCache && threadCache.isLoaded,
            threadIsTemporary: thread && thread.isTemporary,
            threadMassMailing: thread && thread.mass_mailing,
            threadModel: thread && thread.model,
            threadTextInputSendShortcuts: thread && thread.textInputSendShortcuts || [],
            threadView,
            threadViewIsLoading: threadView && threadView.isLoading,
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
        isDoFocus: false,
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
        /**
         * Determines whether this should become focused.
         */
        isDoFocus: Boolean,
        order: {
            type: String,
            validate: prop => ['asc', 'desc'].includes(prop),
        },
        selectedMessageLocalId: {
            type: String,
            optional: true,
        },
        /**
         * Function returns the exact scrollable element from the parent
         * to manage proper scroll heights which affects the load more messages.
         */
        getScrollableElement: {
            type: Function,
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
