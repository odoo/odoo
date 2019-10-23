odoo.define('mail.component.ChatWindowHeader', function (require) {
'use strict';

const Icon = require('mail.component.ThreadIcon');

class ChatWindowHeader extends owl.Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.storeDispatch = owl.hooks.useDispatch();
        this.storeGetters = owl.hooks.useGetters();
        this.storeProps = owl.hooks.useStore((state, props) => {
            const chatWindowLocalId = props.chatWindowLocalId;
            const thread = state.threads[chatWindowLocalId];
            const threadName = thread
                ? this.storeGetters.threadName(chatWindowLocalId)
                : undefined;
            return {
                isMobile: state.isMobile,
                thread,
                threadName,
            };
        });
    }

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
        this.storeDispatch('closeChatWindow', this.props.chatWindowLocalId);
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
                    this.storeDispatch('closeDiscuss'),
            });
        } else {
            this.storeDispatch('openDocument', {
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
        this.storeDispatch('shiftLeftChatWindow', this.props.chatWindowLocalId);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickShiftRight(ev) {
        this.storeDispatch('shiftRightChatWindow', this.props.chatWindowLocalId);
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
