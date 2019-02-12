odoo.define('mail.component.DiscussSidebarItem', function (require) {
'use strict';

const EditableText = require('mail.component.EditableText');
const Icon = require('mail.component.ThreadIcon');

const Dialog = require('web.Dialog');

class DiscussSidebarItem extends owl.store.ConnectedComponent {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.state = owl.useState({
            renaming: false,
        });
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
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
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Element} scrollable
     * @return {boolean}
     */
    isPartiallyVisible({ scrollable }) {
        const elRect = this.el.getBoundingClientRect();
        if (!this.el.parentNode) {
            return false;
        }
        const scrollableRect = scrollable.getBoundingClientRect();
        // intersection with 5px offset
        return (
            elRect.top < scrollableRect.bottom + 5 &&
            scrollableRect.top < elRect.bottom + 5
        );
    }

    scrollIntoview() {
        this.el.scrollIntoView();
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
            Dialog.confirm(
                this,
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
        this.state.renaming = false;
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
    _onClickLeave(ev) {
        let prom;
        if (this.storeProps.thread.create_uid === this.env.session.uid) {
            prom = this._askAdminConfirmation();
        } else {
            prom = Promise.resolve();
        }
        return prom.then(() =>
            this.dispatch('unsubscribeFromChannel', this.props.threadLocalId));
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRename(ev) {
        this.state.renaming = true;
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
        return this.dispatch('unsubscribeFromChannel', this.storeProps.threadLocalId);
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.newName
     */
    _onRename(ev) {
        this.state.renaming = false;
        this.dispatch('renameThread',
            this.props.threadLocalId,
            ev.detail.newName);
    }
}

DiscussSidebarItem.components = {
    EditableText,
    Icon,
};

DiscussSidebarItem.defaultProps = {
    isActive: false,
};

/**
 * @param {Object} state
 * @param {Object} ownProps
 * @param {string} ownProps.threadLocalId
 * @param {Object} state.getters
 * @return {Object}
 */
DiscussSidebarItem.mapStoreToProps = function (state, ownProps, getters) {
    const thread = state.threads[ownProps.threadLocalId];
    const directPartner = thread.directPartnerLocalId
        ? state.partners[thread.directPartnerLocalId]
        : undefined;
    return {
        directPartner,
        thread,
        threadName: getters.threadName(ownProps.threadLocalId),
    };
};

DiscussSidebarItem.props = {
    isActive: Boolean,
    threadLocalId: String,
};

DiscussSidebarItem.template = 'mail.component.DiscussSidebarItem';

return DiscussSidebarItem;

});
