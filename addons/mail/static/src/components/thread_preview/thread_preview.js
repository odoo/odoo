odoo.define('mail/static/src/components/thread_preview/thread_preview.js', function (require) {
'use strict';

const components = {
    MessageAuthorPrefix: require('mail/static/src/components/message_author_prefix/message_author_prefix.js'),
    PartnerImStatusIcon: require('mail/static/src/components/partner_im_status_icon/partner_im_status_icon.js'),
};
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');
const mailUtils = require('mail.utils');

const { Component } = owl;
const { useRef } = owl.hooks;

class ThreadPreview extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            let lastMessageAuthor;
            let lastMessage;
            if (thread) {
                const orderedMessages = thread.orderedMessages;
                lastMessage = orderedMessages[orderedMessages.length - 1];
            }
            if (lastMessage) {
                lastMessageAuthor = lastMessage.author;
            }
            return {
                isDeviceMobile: this.env.messaging.device.isMobile,
                lastMessage: lastMessage ? lastMessage.__state : undefined,
                lastMessageAuthor: lastMessageAuthor
                    ? lastMessageAuthor.__state
                    : undefined,
                thread: thread ? thread.__state : undefined,
                threadCorrespondent: thread && thread.correspondent
                    ? thread.correspondent.__state
                    : undefined,
            };
        });
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
        if (this.thread.correspondent) {
            return this.thread.correspondent.avatarUrl;
        }
        return `/web/image/mail.channel/${this.thread.id}/image_128`;
    }

    /**
     * Get inline content of the last message of this conversation.
     *
     * @returns {string}
     */
    get inlineLastMessageBody() {
        if (!this.thread.lastMessage) {
            return '';
        }
        return mailUtils.htmlToTextContentInline(this.thread.lastMessage.prettyBody);
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
        if (this.thread.lastNonTransientMessage) {
            this.thread.markAsSeen(this.thread.lastNonTransientMessage);
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
