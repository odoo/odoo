odoo.define('mail.component.DiscussSidebarItem', function (require) {
'use strict';

const EditableText = require('mail.component.EditableText');
const Icon = require('mail.component.ThreadIcon');

const Dialog = require('web.Dialog');

const { Component, useState } = owl;
const { useDispatch, useGetters, useStore } = owl.hooks;

class DiscussSidebarItem extends Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.state = useState({
            /**
             * Determine whether this discuss item is currently being renamed.
             */
            isRenaming: false,
        });
        this.storeDispatch = useDispatch();
        this.storeGetters = useGetters();
        this.storeProps = useStore((state, props) => {
            const thread = state.threads[props.threadLocalId];
            const directPartner = thread.directPartnerLocalId
                ? state.partners[thread.directPartnerLocalId]
                : undefined;
            return {
                directPartner,
                thread,
                threadName: this.storeGetters.threadName(props.threadLocalId),
            };
        });
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * Get the counter of this discuss item, which is based on the thread type.
     *
     * @return {integer}
     */
    get counter() {
        if (this.storeProps.thread._model === 'mail.box') {
            return this.storeProps.thread.counter;
        } else if (this.storeProps.thread.channel_type === 'channel') {
            return this.storeProps.thread.message_needaction_counter;
        } else if (this.storeProps.thread.channel_type === 'chat') {
            return this.storeProps.thread.message_unread_counter;
        }
        return 0;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @return {Promise}
     */
    _askAdminConfirmation() {
        return new Promise(resolve => {
            Dialog.confirm(this,
                this.env._t("You are the administrator of this channel. Are you sure you want to leave?"),
                {
                    buttons: [
                        {
                            text: this.env._t("Leave"),
                            classes: 'btn-primary',
                            close: true,
                            click: resolve
                        },
                        {
                            text: this.env._t("Discard"),
                            close: true
                        }
                    ]
                }
            );
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onCancelRenaming(ev) {
        this.state.isRenaming = false;
    }

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
     * Stop propagation to prevent selecting this item.
     *
     * @private
     * @param {CustomEvent} ev
     */
    _onClickedEditableText(ev) {
        ev.stopPropagation();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickLeave(ev) {
        if (this.storeProps.thread.create_uid === this.env.session.uid) {
            await this._askAdminConfirmation();
        }
        this.storeDispatch('unsubscribeFromChannel', this.props.threadLocalId);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRename(ev) {
        this.state.isRenaming = true;
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSettings(ev) {
        return this.env.do_action({
            type: 'ir.actions.act_window',
            res_model: this.storeProps.thread._model,
            res_id: this.storeProps.thread.id,
            views: [[false, 'form']],
            target: 'current'
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickUnpin(ev) {
        return this.storeDispatch('unsubscribeFromChannel', this.storeProps.threadLocalId);
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.newName
     */
    _onRename(ev) {
        this.state.isRenaming = false;
        this.storeDispatch('renameThread',
            this.props.threadLocalId,
            ev.detail.newName);
    }
}

DiscussSidebarItem.components = { EditableText, Icon };

DiscussSidebarItem.defaultProps = {
    isActive: false,
};

DiscussSidebarItem.props = {
    isActive: {
        type: Boolean,
    },
    threadLocalId: String,
};

DiscussSidebarItem.template = 'mail.component.DiscussSidebarItem';

return DiscussSidebarItem;

});
