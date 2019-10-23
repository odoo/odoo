odoo.define('mail.component.ThreadPreview', function (require) {
'use strict';

const MessageAuthorPrefix = require('mail.component.MessageAuthorPrefix');
const PartnerImStatusIcon = require('mail.component.PartnerImStatusIcon');
const mailUtils = require('mail.utils');

const { Component } = owl;
const { useDispatch, useGetters, useStore } = owl.hooks;

class ThreadPreview extends Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.storeDispatch = useDispatch();
        this.storeGetters = useGetters();
        this.storeProps = useStore((state, props) => {
            const threadLocalId = props.threadLocalId;
            const thread = state.threads[threadLocalId];
            let lastMessage;
            let lastMessageAuthor;
            const { length: l, [l - 1]: lastMessageLocalId } = thread.messageLocalIds;
            lastMessage = state.messages[lastMessageLocalId];
            if (lastMessage) {
                lastMessageAuthor = state.partners[lastMessage.authorLocalId];
            }
            return {
                isMobile: state.isMobile,
                lastMessage,
                lastMessageAuthor,
                thread,
                threadDirectPartner: thread.directPartnerLocalId
                    ? state.partners[thread.directPartnerLocalId]
                    : undefined,
                threadName: this.storeGetters.threadName(threadLocalId),
            };
        });
    }

    //--------------------------------------------------------------------------
    // Getter / Setter
    //--------------------------------------------------------------------------

    /**
     * Get the image route of the thread.
     *
     * @return {string}
     */
    get image() {
        const directPartnerLocalId = this.storeProps.thread.directPartnerLocalId;
        if (directPartnerLocalId) {
            const directPartner = this.env.store.state.partners[directPartnerLocalId];
            return `/web/image/res.partner/${directPartner.id}/image_128`;
        }
        return `/web/image/mail.channel/${this.storeProps.thread.id}/image_128`;
    }

    /**
     * Get inline content of the last message of this conversation.
     *
     * @return {string}
     */
    get inlineLastMessageBody() {
        if (!this.storeProps.lastMessage) {
            return '';
        }
        return mailUtils.parseAndTransform(
            this.storeGetters.messagePrettyBody(this.storeProps.lastMessage.localId),
            mailUtils.inline);
    }

    /**
     * Determine whether the last message of this conversation comes from
     * current user or not.
     *
     * @return {boolean}
     */
    get isMyselfLastMessageAuthor() {
        return (
            this.storeProps.lastMessageAuthor &&
            this.storeProps.lastMessageAuthor.id === this.env.session.partner_id
        ) || false;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        this.trigger('o-clicked', {
            threadLocalId: this.props.threadLocalId,
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMarkAsRead(ev) {
        this.storeDispatch('markThreadAsSeen', this.props.threadLocalId);
    }
}

ThreadPreview.components = {
    MessageAuthorPrefix,
    PartnerImStatusIcon,
};

ThreadPreview.props = {
    threadLocalId: String,
};

ThreadPreview.template = 'mail.component.ThreadPreview';

return ThreadPreview;

});
