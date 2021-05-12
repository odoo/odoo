/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { EditableText } from '@mail/components/editable_text/editable_text';
import { PartnerImStatusIcon } from '@mail/components/partner_im_status_icon/partner_im_status_icon';
import { ThreadIcon } from '@mail/components/thread_icon/thread_icon';
import { isEventHandled } from '@mail/utils/utils';

import Dialog from 'web.Dialog';

const { Component } = owl;

const components = { EditableText, PartnerImStatusIcon, ThreadIcon };

export class DiscussSidebarCategoryItem extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useModels();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.discuss_sidebar_category_item}
     */
    get categoryItem() {
        return this.env.models['mail.discuss_sidebar_category_item'].get(this.props.categoryItemLocalId);
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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onCancelRenaming(ev) {
        this.env.messaging.discuss.cancelThreadRenaming(this.categoryItem.channel);
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
        if (this.categoryItem.channel.creator === this.env.messaging.currentUser) {
            await this._askAdminConfirmation();
        }
        this.categoryItem.channel.unsubscribe();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRename(ev) {
        ev.stopPropagation();
        this.env.messaging.discuss.setThreadRenaming(this.categoryItem.channel);
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
        this.env.messaging.discuss.onValidateEditableText(this.categoryItem.channel, ev.detail.newName);
    }

}

Object.assign(DiscussSidebarCategoryItem, {
    components,
    props: {
        categoryItemLocalId: String,
    },
    template: 'mail.DiscussSidebarCategoryItem',
});
