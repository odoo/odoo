odoo.define('mail.messaging.component.ThreadPreview', function (require) {
'use strict';

const components = {
    MessageAuthorPrefix: require('mail.messaging.component.MessageAuthorPrefix'),
    PartnerImStatusIcon: require('mail.messaging.component.PartnerImStatusIcon'),
};
const useStore = require('mail.messaging.component_hook.useStore');
const mailUtils = require('mail.utils');

const { Component } = owl;

class ThreadPreview extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const thread = this.env.entities.Thread.get(props.threadLocalId);
            const mainThreadCache = thread ? thread.mainCache : undefined;
            let lastMessageAuthor;
            let lastMessage;
            if (thread) {
                const orderedMessages = mainThreadCache.orderedMessages;
                lastMessage = orderedMessages[orderedMessages.length - 1];
            }
            if (lastMessage) {
                lastMessageAuthor = lastMessage.author;
            }
            return {
                isDeviceMobile: this.env.messaging.device.isMobile,
                lastMessage,
                lastMessageAuthor,
                thread,
                threadDirectPartner: thread ? thread.directPartner : undefined,
                threadName: thread ? thread.displayName : undefined,
            };
        });
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
        if (this.thread.directPartner) {
            return `/web/image/res.partner/${this.thread.directPartner.id}/image_128`;
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
        return mailUtils.parseAndTransform(this.thread.lastMessage.prettyBody, mailUtils.inline);
    }

    /**
     * Determine whether the last message of this conversation comes from
     * current user or not.
     *
     * @returns {boolean}
     */
    get isMyselfLastMessageAuthor() {
        if (!this.thread.lastMessage) {
            return false;
        }
        if (!this.thread.lastMessage.author) {
            return false;
        }
        return this.thread.lastMessage.author === this.env.messaging.currentPartner;
    }

    /**
     * @returns {mail.messaging.entity.Thread}
     */
    get thread() {
        return this.env.entities.Thread.get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        this.trigger('o-select-thread', { thread: this.thread.localId });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMarkAsRead(ev) {
        this.thread.markAsSeen();
    }

}

Object.assign(ThreadPreview, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.messaging.component.ThreadPreview',
});

return ThreadPreview;

});
