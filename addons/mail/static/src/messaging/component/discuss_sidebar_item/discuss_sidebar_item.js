odoo.define('mail.messaging.component.DiscussSidebarItem', function (require) {
'use strict';

const components = {
    EditableText: require('mail.messaging.component.EditableText'),
    ThreadIcon: require('mail.messaging.component.ThreadIcon'),
};
const useStore = require('mail.messaging.component_hook.useStore');

const Dialog = require('web.Dialog');

const { Component } = owl;

class DiscussSidebarItem extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const thread = this.env.entities.Thread.get(props.threadLocalId);
            const directPartner = thread ? thread.directPartner : undefined;
            return {
                directPartner,
                discuss: this.env.messaging.discuss,
                thread,
                threadName: thread ? thread.displayName : undefined,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the counter of this discuss item, which is based on the thread type.
     *
     * @returns {integer}
     */
    get counter() {
        if (this.thread.model === 'mail.box') {
            return this.thread.counter;
        } else if (this.thread.channel_type === 'channel') {
            return this.thread.message_needaction_counter;
        } else if (this.thread.channel_type === 'chat') {
            return this.thread.message_unread_counter;
        }
        return 0;
    }

    /**
     * @returns {mail.messaging.entity.Discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.discuss;
    }

    /**
     * @returns {boolean}
     */
    hasUnpin() {
        return this.thread.channel_type === 'chat';
    }

    /**
     * @returns {mail.messaging.entity.Thread}
     */
    get thread() {
        return this.env.entities.Thread.get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Promise}
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
        this.discuss.cancelRenaming(this.thread);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        this.discuss.update({ thread: this.thread });
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
        ev.stopPropagation();
        if (this.thread.create_uid === this.env.session.uid) {
            await this._askAdminConfirmation();
        }
        this.thread.unsubscribe();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRename(ev) {
        ev.stopPropagation();
        this.discuss.setRenaming(this.thread);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSettings(ev) {
        ev.stopPropagation();
        return this.env.do_action({
            type: 'ir.actions.act_window',
            res_model: this.thread.model,
            res_id: this.thread.id,
            views: [[false, 'form']],
            target: 'current'
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickUnpin(ev) {
        ev.stopPropagation();
        this.thread.unsubscribe();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.newName
     */
    _onValidateEditableText(ev) {
        ev.stopPropagation();
        this.thread.rename(ev.detail.newName);
    }

}

Object.assign(DiscussSidebarItem, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.messaging.component.DiscussSidebarItem',
});

return DiscussSidebarItem;

});
