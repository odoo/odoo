odoo.define('mail/static/src/components/messaging_menu/messaging_menu.js', function (require) {
'use strict';

const components = {
    AutocompleteInput: require('mail/static/src/components/autocomplete_input/autocomplete_input.js'),
    MobileMessagingNavbar: require('mail/static/src/components/mobile_messaging_navbar/mobile_messaging_navbar.js'),
    NotificationList: require('mail/static/src/components/notification_list/notification_list.js'),
};
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const patchMixin = require('web.patchMixin');

const { Component } = owl;

class MessagingMenu extends Component {

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
        useShouldUpdateBasedOnProps();
        useStore(props => {
            return {
                isDeviceMobile: this.env.messaging && this.env.messaging.device.isMobile,
                isDiscussOpen: this.env.messaging && this.env.messaging.discuss.isOpen,
                isMessagingInitialized: this.env.isMessagingInitialized(),
                messagingMenu: this.env.messaging && this.env.messaging.messagingMenu.__state,
            };
        });

        // bind since passed as props
        this._onMobileNewMessageInputSelect = this._onMobileNewMessageInputSelect.bind(this);
        this._onMobileNewMessageInputSource = this._onMobileNewMessageInputSource.bind(this);
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
        this.messagingMenu.update({ activeTabId: ev.currentTarget.dataset.tabId });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickNewMessage(ev) {
        if (!this.env.messaging.device.isMobile) {
            this.env.messaging.chatWindowManager.openNewMessage();
            this.messagingMenu.close();
        } else {
            this.messagingMenu.toggleMobileNewMessage();
        }
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
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    _onMobileNewMessageInputSelect(ev, ui) {
        this.env.messaging.openChat({ partnerId: ui.item.id });
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onMobileNewMessageInputSource(req, res) {
        const value = _.escape(req.term);
        this.env.models['mail.partner'].imSearch({
            callback: partners => {
                const suggestions = partners.map(partner => {
                    return {
                        id: partner.id,
                        value: partner.nameOrDisplayName,
                        label: partner.nameOrDisplayName,
                    };
                });
                res(_.sortBy(suggestions, 'label'));
            },
            keyword: value,
            limit: 10,
        });
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

return patchMixin(MessagingMenu);

});
