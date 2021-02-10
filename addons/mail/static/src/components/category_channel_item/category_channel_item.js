odoo.define('mail/static/src/components/category_channel_item/category_channel_item.js', function (require) {
'use strict';

const components = {
    CategoryItem: require('mail/static/src/components/category_item/category_item.js'),
    ThreadIcon: require('mail/static/src/components/thread_icon/thread_icon.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const Dialog = require('web.Dialog');

const { Component } = owl;

class CategoryChannelItem extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                thread: thread ? thread.__state : undefined,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {String}
     */
    get image() {
        return `/web/image/mail.channel/${this.thread.id}/image_128`;
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
     * @param {MouseEvent} ev
     */
    async _onClickLeave(ev) {
        ev.stopPropagation();
        if (this.thread.creator === this.env.messaging.currentUser) {
            await this._askAdminConfirmation();
        }
        this.thread.unsubscribe();
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
                res_model: this.thread.model,
                res_id: this.thread.id,
                views: [[false, 'form']],
                target: 'current'
            },
        });
    }
}

Object.assign(CategoryChannelItem, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.CategoryChannelItem',
});

return CategoryChannelItem;

});
