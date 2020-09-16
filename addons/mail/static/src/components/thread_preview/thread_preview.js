odoo.define('mail/static/src/components/thread_preview/thread_preview.js', function (require) {
'use strict';

const components = {
    MessageAuthorPrefix: require('mail/static/src/components/message_author_prefix/message_author_prefix.js'),
    PartnerImStatusIcon: require('mail/static/src/components/partner_im_status_icon/partner_im_status_icon.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');
const mailUtils = require('mail.utils');

const { Component } = owl;
const { useRef } = owl.hooks;

class ThreadPreview extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
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
        if (this.thread.__mfield_correspondent(this)) {
            return `/web/image/res.partner/${this.thread.__mfield_correspondent(this).__mfield_id(this)}/image_128`;
        }
        return `/web/image/mail.channel/${this.thread.__mfield_id(this)}/image_128`;
    }

    /**
     * Get inline content of the last message of this conversation.
     *
     * @returns {string}
     */
    get inlineLastMessageBody() {
        if (!this.thread.__mfield_lastMessage(this)) {
            return '';
        }
        return mailUtils.htmlToTextContentInline(this.thread.__mfield_lastMessage(this).__mfield_prettyBody(this));
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
        if (!this.env.messaging.__mfield_device(this).__mfield_isMobile(this)) {
            this.env.messaging.__mfield_messagingMenu(this).close();
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMarkAsRead(ev) {
        if (this.thread.__mfield_lastMessage(this)) {
            this.thread.markAsSeen(this.thread.__mfield_lastMessage(this).__mfield_id(this));
        }
    }

}

Object.assign(ThreadPreview, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.ThreadPreview',
});

return ThreadPreview;

});
