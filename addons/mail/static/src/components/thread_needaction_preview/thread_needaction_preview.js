/** @odoo-module **/

import * as mailUtils from '@mail/js/utils';

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadNeedactionPreview extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'markAsReadRef', modelName: 'ThreadNeedactionPreviewView', refName: 'markAsRead' });
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
        if (this.threadNeedactionPreviewView.thread.moduleIcon) {
            return this.threadNeedactionPreviewView.thread.moduleIcon;
        }
        if (this.threadNeedactionPreviewView.thread.correspondent) {
            return this.threadNeedactionPreviewView.thread.correspondent.avatarUrl;
        }
        if (this.threadNeedactionPreviewView.thread.model === 'mail.channel') {
            return `/web/image/mail.channel/${this.threadNeedactionPreviewView.thread.id}/avatar_128?unique=${this.threadNeedactionPreviewView.thread.avatarCacheKey}`;
        }
        return '/mail/static/src/img/smiley/avatar.jpg';
    }

    /**
     * Get inline content of the last message of this conversation.
     *
     * @returns {string}
     */
    get inlineLastNeedactionMessageAsOriginThreadBody() {
        if (!this.threadNeedactionPreviewView.thread.lastNeedactionMessageAsOriginThread) {
            return '';
        }
        return mailUtils.htmlToTextContentInline(this.threadNeedactionPreviewView.thread.lastNeedactionMessageAsOriginThread.prettyBody);
    }

    /**
     * @returns {ThreadNeedactionPreviewView}
     */
    get threadNeedactionPreviewView() {
        return this.messaging && this.messaging.models['ThreadNeedactionPreviewView'].get(this.props.localId);
    }

}

Object.assign(ThreadNeedactionPreview, {
    props: { localId: String },
    template: 'mail.ThreadNeedactionPreview',
});

registerMessagingComponent(ThreadNeedactionPreview);
