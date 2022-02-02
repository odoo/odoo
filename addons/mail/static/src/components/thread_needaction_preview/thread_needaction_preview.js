/** @odoo-module **/

import * as mailUtils from '@mail/js/utils';

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, useRef } = owl;

export class ThreadNeedactionPreview extends Component {

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
        this.threadNeedactionPreviewView.thread.open();
        if (!this.messaging.device.isMobile) {
            this.messaging.messagingMenu.close();
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMarkAsRead(ev) {
        this.messaging.models['Message'].markAllAsRead([
            ['model', '=', this.threadNeedactionPreviewView.thread.model],
            ['res_id', '=', this.threadNeedactionPreviewView.thread.id],
        ]);
    }

}

Object.assign(ThreadNeedactionPreview, {
    props: { localId: String },
    template: 'mail.ThreadNeedactionPreview',
});

registerMessagingComponent(ThreadNeedactionPreview);
