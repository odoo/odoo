odoo.define('mail/static/src/components/discuss_sidebar_item/discuss_sidebar_item.js', function (require) {
'use strict';

const components = {
    EditableText: require('mail/static/src/components/editable_text/editable_text.js'),
    ThreadIcon: require('mail/static/src/components/thread_icon/thread_icon.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const Dialog = require('web.Dialog');

const { Component } = owl;

class DiscussSidebarItem extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
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
        if (this.thread.__mfield_model(this) === 'mail.box') {
            return this.thread.__mfield_counter(this);
        } else if (this.thread.__mfield_channel_type(this) === 'channel') {
            return this.thread.__mfield_message_needaction_counter(this);
        } else if (this.thread.__mfield_channel_type(this) === 'chat') {
            return this.thread.__mfield_localMessageUnreadCounter(this);
        }
        return 0;
    }

    /**
     * @returns {mail.discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.__mfield_discuss(this);
    }

    /**
     * @returns {boolean}
     */
    hasUnpin() {
        return this.thread.__mfield_channel_type(this) === 'chat';
    }

    /**
     * @returns {mail.thread}
     */
    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
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
        this.discuss.cancelThreadRenaming(this.thread);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        this.thread.open();
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
        if (this.thread.__mfield_creator(this) === this.env.messaging.__mfield_currentUser(this)) {
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
        this.discuss.setThreadRenaming(this.thread);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSettings(ev) {
        ev.stopPropagation();
        return this.env.bus.trigger('do-action', {
            action: {
                type: 'ir.actions.act_window',
                res_model: this.thread.__mfield_model(this),
                res_id: this.thread.__mfield_id(this),
                views: [[false, 'form']],
                target: 'current'
            },
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
        this.discuss.renameThread(this.thread, ev.detail.newName);
    }

}

Object.assign(DiscussSidebarItem, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.DiscussSidebarItem',
});

return DiscussSidebarItem;

});
