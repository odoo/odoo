/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { isEventHandled } from '@mail/utils/utils';

import Dialog from 'web.Dialog';

const { Component } = owl;

export class DiscussSidebarCategoryItem extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.discuss_sidebar_category_item}
     */
    get categoryItem() {
        return this.messaging.models['mail.discuss_sidebar_category_item'].get(this.props.categoryItemLocalId);
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
                            click: resolve,
                        },
                        {
                            text: this.env._t("Discard"),
                            close: true,
                        },
                    ],
                }
            );
        });
    }

    /**
     * @private
     * @returns {Promise}
     */
    _askLeaveGroupConfirmation() {
        return new Promise(resolve => {
            Dialog.confirm(this,
                this.env._t("You are about to leave this group conversation and will no longer have access to it unless you are invited again. Are you sure you want to continue?"),
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
        this.messaging.discuss.cancelThreadRenaming(this.categoryItem.channel);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        if (isEventHandled(ev, 'EditableText.click')) {
            return;
        }
        this.categoryItem.channel.open();
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
        if (this.categoryItem.channel.channel_type !== 'group' && this.categoryItem.channel.creator === this.messaging.currentUser) {
            await this._askAdminConfirmation();
        }
        if (this.categoryItem.channel.channel_type === 'group' && this.categoryItem.channel.members.length > 1) {
            await this._askLeaveGroupConfirmation();
        }
        this.categoryItem.channel.unsubscribe();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRename(ev) {
        ev.stopPropagation();
        this.messaging.discuss.setThreadRenaming(this.categoryItem.channel);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSettings(ev) {
        ev.stopPropagation();
        return this.categoryItem._onClickSettingsCommand();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickUnpin(ev) {
        ev.stopPropagation();
        this.categoryItem.channel.unsubscribe();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.newName
     */
    _onValidateEditableText(ev) {
        ev.stopPropagation();
        this.messaging.discuss.onValidateEditableText(this.categoryItem.channel, ev.detail.newName);
    }

}

Object.assign(DiscussSidebarCategoryItem, {
    props: {
        categoryItemLocalId: String,
    },
    template: 'mail.DiscussSidebarCategoryItem',
});

registerMessagingComponent(DiscussSidebarCategoryItem);
