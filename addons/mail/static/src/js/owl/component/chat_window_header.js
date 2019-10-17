odoo.define('mail.component.ChatWindowHeader', function (require) {
'use strict';

const Icon = require('mail.component.ThreadIcon');

class ChatWindowHeader extends owl.store.ConnectedComponent {

    //--------------------------------------------------------------------------
    // Getter / Setter
    //--------------------------------------------------------------------------

    get name() {
        if (this.storeProps.thread) {
            return this.storeProps.threadName;
        }
        return this.env._t("New message");
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
            chatWindowLocalId: this.props.chatWindowLocalId,
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickClose(ev) {
        this.dispatch('closeChatWindow', this.props.chatWindowLocalId);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickExpand(ev) {
        if (!this.storeProps.thread) {
            return;
        }
        if (['mail.channel', 'mail.box'].includes(this.storeProps.thread._model)) {
            this.env.do_action('mail.action_owl_discuss', {
                clear_breadcrumbs: false,
                active_id: this.storeProps.thread.localId,
                on_reverse_breadcrumb: () =>
                    // ideally discuss should do it itself...
                    this.dispatch('closeDiscuss'),
            });
        } else {
            this.dispatch('openDocument', {
                id: this.storeProps.thread.id,
                model: this.storeProps.thread._model,
            });
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickShiftLeft(ev) {
        this.dispatch('shiftLeftChatWindow', this.props.chatWindowLocalId);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickShiftRight(ev) {
        this.dispatch('shiftRightChatWindow', this.props.chatWindowLocalId);
    }
}

ChatWindowHeader.components = {
    Icon,
};

ChatWindowHeader.defaultProps = {
    hasCloseAsBackButton: false,
    hasShiftLeft: false,
    hasShiftRight: false,
    isExpandable: false,
};

/**
 * @param {Object} state
 * @param {Object} ownProps
 * @param {string} ownProps.chatWindowLocalId
 * @param {Object} state.getters
 * @return {Object}
 */
ChatWindowHeader.mapStoreToProps = function (state, ownProps, getters) {
    const chatWindowLocalId = ownProps.chatWindowLocalId;
    const thread = state.threads[chatWindowLocalId];
    const threadName = thread
        ? getters.threadName(chatWindowLocalId)
        : undefined;
    return {
        isMobile: state.isMobile,
        thread,
        threadName,
    };
};

ChatWindowHeader.props = {
    chatWindowLocalId: String,
    hasCloseAsBackButton: Boolean,
    hasShiftLeft: Boolean,
    hasShiftRight: Boolean,
    isExpandable: Boolean,
};

ChatWindowHeader.template = 'mail.component.ChatWindowHeader';

return ChatWindowHeader;

});
