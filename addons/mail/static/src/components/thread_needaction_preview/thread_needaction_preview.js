odoo.define('mail/static/src/components/thread_needaction_preview/thread_needaction_preview.js', function (require) {
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

class ThreadNeedactionPreview extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            const mainThreadCache = thread ? thread.mainCache : undefined;
            let lastNeedactionMessageAsOriginThreadAuthor;
            let lastNeedactionMessageAsOriginThread;
            let threadCorrespondent;
            if (thread) {
                lastNeedactionMessageAsOriginThread = mainThreadCache.lastNeedactionMessageAsOriginThread;
                threadCorrespondent = thread.correspondent;
            }
            if (lastNeedactionMessageAsOriginThread) {
                lastNeedactionMessageAsOriginThreadAuthor = lastNeedactionMessageAsOriginThread.author;
            }
            return {
                isDeviceMobile: this.env.messaging.device.isMobile,
                lastNeedactionMessageAsOriginThread: lastNeedactionMessageAsOriginThread ? lastNeedactionMessageAsOriginThread.__state : undefined,
                lastNeedactionMessageAsOriginThreadAuthor: lastNeedactionMessageAsOriginThreadAuthor
                    ? lastNeedactionMessageAsOriginThreadAuthor.__state
                    : undefined,
                thread: thread ? thread.__state : undefined,
                threadCorrespondent: threadCorrespondent
                    ? threadCorrespondent.__state
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
    get inlineLastNeedactionMessageBody() {
        if (!this.thread.lastNeedactionMessage) {
            return '';
        }
        return mailUtils.htmlToTextContentInline(this.thread.lastNeedactionMessage.prettyBody);
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

return ThreadNeedactionPreview;

});
