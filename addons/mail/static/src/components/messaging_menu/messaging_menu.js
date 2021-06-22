/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { AutocompleteInput } from '@mail/components/autocomplete_input/autocomplete_input';
import { MobileMessagingNavbar } from '@mail/components/mobile_messaging_navbar/mobile_messaging_navbar';
import { NotificationList } from '@mail/components/notification_list/notification_list';

const { Component } = owl;

const components = {
    AutocompleteInput,
    MobileMessagingNavbar,
    NotificationList,
};

export class MessagingMenu extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        /**
         * global JS generated ID for this component. Useful to provide a
         * custom class to autocomplete input, so that click in an autocomplete
         * item is not considered as a click away from messaging menu in mobile.
         */
        this.id = _.uniqueId('o_messagingMenu_');
        useModels();
        useShouldUpdateBasedOnProps();

        // bind since passed as props
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
        this._constructor(...args);
    }

    /**
     * Allows patching constructor.
     */
    _constructor() {}

    mounted() {
        document.addEventListener('click', this._onClickCaptureGlobal, true);
    }

    willUnmount() {
        document.removeEventListener('click', this._onClickCaptureGlobal, true);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.discuss;
    }

    /**
     * @returns {mail.messaging_menu}
     */
    get messagingMenu() {
        return this.env.messaging && this.env.messaging.messagingMenu;
    }

    /**
     * @returns {string}
     */
    get mobileNewMessageInputPlaceholder() {
        return this.env._t("Search user...");
    }

    /**
     * @returns {Object[]}
     */
    get tabs() {
        return [{
            icon: 'fa fa-envelope',
            id: 'all',
            label: this.env._t("All"),
        }, {
            icon: 'fa fa-user',
            id: 'chat',
            label: this.env._t("Chat"),
        }, {
            icon: 'fa fa-users',
            id: 'channel',
            label: this.env._t("Channel"),
        }];
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Closes the menu when clicking outside, if appropriate.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        if (!this.env.messaging) {
            /**
             * Messaging not created, which means essential models like
             * messaging menu are not ready, so user interactions are omitted
             * during this (short) period of time.
             */
            return;
        }
        // ignore click inside the menu
        if (this.el.contains(ev.target)) {
            return;
        }
        // in all other cases: close the messaging menu when clicking outside
        this.messagingMenu.close();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDesktopTabButton(ev) {
        this.messagingMenu.onClickDesktopTabButton(ev);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickToggler(ev) {
        // avoid following dummy href
        ev.preventDefault();
        if (!this.env.messaging) {
            /**
             * Messaging not created, which means essential models like
             * messaging menu are not ready, so user interactions are omitted
             * during this (short) period of time.
             */
            return;
        }
        this.messagingMenu.toggleOpen();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onHideMobileNewMessage(ev) {
        ev.stopPropagation();
        this.messagingMenu.toggleMobileNewMessage();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.tabId
     */
    _onSelectMobileNavbarTab(ev) {
        ev.stopPropagation();
        this.messagingMenu.update({ activeTabId: ev.detail.tabId });
    }

}

Object.assign(MessagingMenu, {
    components,
    props: {},
    template: 'mail.MessagingMenu',
});
