/** @odoo-module **/

import * as mailUtils from '@mail/js/utils';

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, useRef } = owl;

export class ThreadPreview extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        /**
         * Reference of the "mark as read" button. Useful to disable the
         * top-level click handler when clicking on this specific button.
         */
        this._markAsReadRef = useRef('markAsRead');
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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        const markAsRead = this._markAsReadRef.el;
        if (markAsRead && markAsRead.contains(ev.target)) {
            // handled in `_onClickMarkAsRead`
            return;
        }
        this.threadPreviewView.thread.open();
        if (!this.messaging.device.isMobile) {
            this.messaging.messagingMenu.close();
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMarkAsRead(ev) {
        if (this.threadPreviewView.thread.lastNonTransientMessage) {
            this.threadPreviewView.thread.markAsSeen(this.threadPreviewView.thread.lastNonTransientMessage);
        }
    }

}

Object.assign(ThreadPreview, {
    props: { localId: String },
    template: 'mail.ThreadPreview',
});

registerMessagingComponent(ThreadPreview);
