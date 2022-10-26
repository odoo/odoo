/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadNeedactionPreview extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'markAsReadRef', refName: 'markAsRead' });
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
        if (!this.threadNeedactionPreviewView.thread.channel) {
            return '/mail/static/src/img/smiley/avatar.jpg';
        }
        if (this.threadNeedactionPreviewView.thread.channel.correspondent) {
            return this.threadNeedactionPreviewView.thread.channel.correspondent.avatarUrl;
        }
        return `/web/image/mail.channel/${this.threadNeedactionPreviewView.thread.id}/avatar_128?unique=${this.threadNeedactionPreviewView.thread.channel.avatarCacheKey}`;
    }

    /**
     * @returns {ThreadNeedactionPreviewView}
     */
    get threadNeedactionPreviewView() {
        return this.props.record;
    }

}

Object.assign(ThreadNeedactionPreview, {
    props: { record: Object },
    template: 'mail.ThreadNeedactionPreview',
});

registerMessagingComponent(ThreadNeedactionPreview);
