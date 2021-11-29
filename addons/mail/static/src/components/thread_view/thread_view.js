/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;
const { useRef } = owl.hooks;

export class ThreadView extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the scroll height in the message list.
     *
     * @returns {integer|undefined}
     */
    getScrollHeight() {
        if (!this.refs.messageList) {
            return undefined;
        }
        return this.refs.messageList.getScrollHeight();
    }

    /**
     * Get the scroll position in the message list.
     *
     * @returns {integer|undefined}
     */
    getScrollTop() {
        if (!this.refs.messageList) {
            return undefined;
        }
        return this.refs.messageList.getScrollTop();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    onScroll(ev) {
        if (!this.refs.messageList) {
            return;
        }
        this.refs.messageList.onScroll(ev);
    }

    /**
     * @returns {mail.thread_view}
     */
    get threadView() {
        return this.messaging && this.messaging.models['mail.thread_view'].get(this.props.threadViewLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickRetryLoadMessages() {
        if (!this.threadView) {
            return;
        }
        if (!this.threadView.threadCache) {
            return;
        }
        this.threadView.threadCache.update({ hasLoadingFailed: false });
    }

}

Object.assign(ThreadView, {
    defaultProps: {
        hasComposerDiscardButton: false,
        hasComposerThreadName: false,
        showComposerAttachmentsExtensions: true,
        showComposerAttachmentsFilenames: true,
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
        hasComposerCurrentPartnerAvatar: {
            type: Boolean,
            optional: true,
        },
        hasComposerDiscardButton: {
            type: Boolean,
            optional: true,
        },
        hasComposerSendButton: {
            type: Boolean,
            optional: true,
        },
        hasComposerThreadName: {
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
        hasScrollAdjust: {
            type: Boolean,
            optional: true,
        },
        onFocusin: {
            type: Function,
            optional: true,
        },
        showComposerAttachmentsExtensions: Boolean,
        showComposerAttachmentsFilenames: Boolean,
        threadViewLocalId: String,
    },
    template: 'mail.ThreadView',
});

registerMessagingComponent(ThreadView);
