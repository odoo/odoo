/** @odoo-module **/

import * as mailUtils from '@mail/js/utils';

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;
const { useRef } = owl.hooks;

export class ThreadNeedactionPreview extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
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
        if (this.thread.moduleIcon) {
            return this.thread.moduleIcon;
        }
        if (this.thread.correspondent) {
            return this.thread.correspondent.avatarUrl;
        }
        if (this.thread.model === 'mail.channel') {
            return `/web/image/mail.channel/${this.thread.id}/avatar_128?unique=${this.thread.avatarCacheKey}`;
        }
        return '/mail/static/src/img/smiley/avatar.jpg';
    }

    /**
     * Get inline content of the last message of this conversation.
     *
     * @returns {string}
     */
    get inlineLastNeedactionMessageAsOriginThreadBody() {
        if (!this.thread.lastNeedactionMessageAsOriginThread) {
            return '';
        }
        return mailUtils.htmlToTextContentInline(this.thread.lastNeedactionMessageAsOriginThread.prettyBody);
    }

    /**
     * @returns {mail.thread}
     */
    get thread() {
        return this.messaging && this.messaging.models['mail.thread'].get(this.props.threadLocalId);
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
        this.thread.open();
        if (!this.messaging.device.isMobile) {
            this.messaging.messagingMenu.close();
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMarkAsRead(ev) {
        this.messaging.models['mail.message'].markAllAsRead([
            ['model', '=', this.thread.model],
            ['res_id', '=', this.thread.id],
        ]);
    }

}

Object.assign(ThreadNeedactionPreview, {
    props: {
        threadLocalId: String,
    },
    template: 'mail.ThreadNeedactionPreview',
});

registerMessagingComponent(ThreadNeedactionPreview);
