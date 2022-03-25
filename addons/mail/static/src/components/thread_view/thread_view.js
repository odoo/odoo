/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadView extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ThreadView}
     */
    get threadView() {
        return this.messaging && this.messaging.models['ThreadView'].get(this.props.localId);
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
        showComposerAttachmentsExtensions: true,
        showComposerAttachmentsFilenames: true,
        onFocusin: () => {},
    },
    props: {
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
        hasScrollAdjust: {
            type: Boolean,
            optional: true,
        },
        localId: String,
        onFocusin: {
            type: Function,
            optional: true,
        },
        showComposerAttachmentsExtensions: {
            type: Boolean,
            optional: true,
        },
        showComposerAttachmentsFilenames: {
            type: Boolean,
            optional: true,
        },
    },
    template: 'mail.ThreadView',
});

registerMessagingComponent(ThreadView);
