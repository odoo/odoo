/** @odoo-module **/

import * as mailUtils from '@mail/js/utils';

import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { MessageAuthorPrefix } from '@mail/components/message_author_prefix/message_author_prefix';
import { PartnerImStatusIcon } from '@mail/components/partner_im_status_icon/partner_im_status_icon';

const { Component } = owl;
const { useRef } = owl.hooks;

const components = { MessageAuthorPrefix, PartnerImStatusIcon };

export class ThreadNeedactionPreview extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useModels();
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
            return `/web/image/mail.channel/${this.thread.id}/image_128`;
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
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
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
        if (!this.env.messaging.device.isMobile) {
            this.env.messaging.messagingMenu.close();
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMarkAsRead(ev) {
        this.env.models['mail.message'].markAllAsRead([
            ['model', '=', this.thread.model],
            ['res_id', '=', this.thread.id],
        ]);
    }

}

Object.assign(ThreadNeedactionPreview, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.ThreadNeedactionPreview',
});
