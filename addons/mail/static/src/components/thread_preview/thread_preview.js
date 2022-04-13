/** @odoo-module **/

import * as mailUtils from '@mail/js/utils';

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadPreview extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'markAsReadRef', modelName: 'ThreadPreviewView', refName: 'markAsRead' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the image route of the thread.
     *
     * @returns {string}
     */
    image() {
        if (this.threadPreviewView.thread.correspondent) {
            return this.threadPreviewView.thread.correspondent.avatarUrl;
        }
        return `/web/image/mail.channel/${this.threadPreviewView.thread.id}/avatar_128?unique=${this.threadPreviewView.thread.avatarCacheKey}`;
    }

    /**
     * Get inline content of the last message of this conversation.
     *
     * @returns {string}
     */
    get inlineLastMessageBody() {
        if (!this.threadPreviewView.thread.lastMessage) {
            return '';
        }
        return mailUtils.htmlToTextContentInline(this.threadPreviewView.thread.lastMessage.prettyBody);
    }

    /**
     * @returns {ThreadPreviewView}
     */
    get threadPreviewView() {
        return this.messaging && this.messaging.models['ThreadPreviewView'].get(this.props.localId);
    }

}

Object.assign(ThreadPreview, {
    props: { localId: String },
    template: 'mail.ThreadPreview',
});

registerMessagingComponent(ThreadPreview);
