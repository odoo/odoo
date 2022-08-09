/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadPreview extends Component {

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
        if (!this.threadPreviewView.thread.channel) {
            return '/mail/static/src/img/smiley/avatar.jpg';
        }
        if (this.threadPreviewView.thread.channel.correspondent) {
            return this.threadPreviewView.thread.channel.correspondent.avatarUrl;
        }
        return `/web/image/mail.channel/${this.threadPreviewView.thread.id}/avatar_128?unique=${this.threadPreviewView.thread.channel.avatarCacheKey}`;
    }

    /**
     * @returns {ThreadPreviewView}
     */
    get threadPreviewView() {
        return this.props.record;
    }

}

Object.assign(ThreadPreview, {
    props: { record: Object },
    template: 'mail.ThreadPreview',
});

registerMessagingComponent(ThreadPreview);
