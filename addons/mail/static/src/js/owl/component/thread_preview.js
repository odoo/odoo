odoo.define('mail.component.ThreadPreview', function (require) {
'use strict';

const MessageAuthorPrefix = require('mail.component.MessageAuthorPrefix');
const PartnerImStatusIcon = require('mail.component.PartnerImStatusIcon');
const mailUtils = require('mail.utils');

class ThreadPreview extends owl.Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.storeDispatch = owl.hooks.useDispatch();
        this.storeGetters = owl.hooks.useGetters();
        this.storeProps = owl.hooks.useStore((state, props) => {
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
     * @return {boolean}
     */
    get isMyselfLastMessageAuthor() {
        return (
            this.storeProps.lastMessageAuthor &&
            this.storeProps.lastMessageAuthor.id === this.env.session.partner_id
        ) || false;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {boolean}
     */
    isPartiallyVisible() {
        const elRect = this.el.getBoundingClientRect();
        if (!this.el.parentNode) {
            return false;
        }
        const parentRect = this.el.parentNode.getBoundingClientRect();
        // intersection with 20px offset
        return (
            elRect.top < parentRect.bottom + 20 &&
            parentRect.top < elRect.bottom + 20
        );
    }

    scrollIntoView() {
        this.el.scrollIntoView();
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
