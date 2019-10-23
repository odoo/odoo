odoo.define('mail.component.ThreadPreviewList', function (require) {
'use strict';

const ThreadPreview = require('mail.component.ThreadPreview');

class ThreadPreviewList extends owl.Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.storeDispatch = owl.hooks.useDispatch();
        this.storeGetters = owl.hooks.useGetters();
        this.storeProps = owl.hooks.useStore((state, props) => {
            let threadLocalIds;
            if (props.filter === 'mailbox') {
                threadLocalIds = this.storeGetters.mailboxList().map(mailbox => mailbox.localId);
            } else if (props.filter === 'channel') {
                threadLocalIds = this.storeGetters.channelList().map(channel => channel.localId);
            } else if (props.filter === 'chat') {
                threadLocalIds = this.storeGetters.chatList().map(chat => chat.localId);
            } else {
                // "All" filter is for channels and chats
                threadLocalIds = this.storeGetters.mailChannelList().map(mailChannel => mailChannel.localId);
            }
            return {
                isMobile: state.isMobile,
                threadLocalIds,
            };
        });
    }

    mounted() {
        this._loadPreviews();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {string} threadLocalId
     * @return {boolean}
     */
    isPreviewPartiallyVisible(threadLocalId) {
        return this.__owl__.refs[threadLocalId].isPartiallyVisible();
    }

    /**
     * @param {string} threadLocalId
     */
    scrollToPreview(threadLocalId) {
        this.__owl__.refs[threadLocalId].scrollIntoView();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _loadPreviews() {
        this.storeDispatch('loadThreadPreviews', this.storeProps.threadLocalIds);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.threadLocalId
     */
    _onClickedPreview(ev) {
        this.trigger('o-select-thread', {
            threadLocalId: ev.detail.threadLocalId,
        });
    }
}

ThreadPreviewList.components = {
    ThreadPreview,
};

ThreadPreviewList.defaultProps = {
    filter: 'all',
};

ThreadPreviewList.props = {
    filter: String, // ['all', 'mailbox', 'channel', 'chat']
    targetThreadLocalId: {
        type: String,
        optional: true,
    },
};

ThreadPreviewList.template = 'mail.component.ThreadPreviewList';

return ThreadPreviewList;

});
