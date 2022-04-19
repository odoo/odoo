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

}

Object.assign(ThreadView, {
    defaultProps: {
        hasComposerDiscardButton: false,
        showComposerAttachmentsExtensions: true,
        showComposerAttachmentsFilenames: true,
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
