odoo.define('mail.component.ThreadPreviewList', function (require) {
'use strict';

const ThreadPreview = require('mail.component.ThreadPreview');

class ThreadPreviewList extends owl.store.ConnectedComponent {

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
        this.dispatch('loadThreadPreviews', this.storeProps.threadLocalIds);
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

/**
 * @param {Object} state
 * @param {Object} ownProps
 * @param {string} ownProps.filter
 * @param {Object} getters
 * @return {Object}
 */
ThreadPreviewList.mapStoreToProps = function (state, ownProps, getters) {
    let threadLocalIds;
    if (ownProps.filter === 'mailbox') {
        threadLocalIds = getters.mailboxList().map(mailbox => mailbox.localId);
    } else if (ownProps.filter === 'channel') {
        threadLocalIds = getters.channelList().map(channel => channel.localId);
    } else if (ownProps.filter === 'chat') {
        threadLocalIds = getters.chatList().map(chat => chat.localId);
    } else {
        // "All" filter is for channels and chats
        threadLocalIds = getters.mailChannelList().map(mailChannel => mailChannel.localId);
    }
    return {
        isMobile: state.isMobile,
        threadLocalIds,
    };
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
