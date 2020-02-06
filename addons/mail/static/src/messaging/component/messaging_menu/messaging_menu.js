odoo.define('mail.messaging.component.MessagingMenu', function (require) {
'use strict';

const components = {
    AutocompleteInput: require('mail.messaging.component.AutocompleteInput'),
    MobileMessagingNavbar: require('mail.messaging.component.MobileMessagingNavbar'),
    NotificationList: require('mail.messaging.component.NotificationList'),
};
const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;
const { useRef } = owl.hooks;

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
        useStore((...args) => this._useStoreSelector(...args));

        /**
         * Reference of the new message input in mobile. Useful to include it
         * and autocomplete menu as "inside" the messaging menu, to prevent
         * closing the messaging menu otherwise.
         */
        this._mobileNewMessageInputRef = useRef('mobileNewMessageInput');

        // bind since passed as props
        this._onMobileNewMessageInputSelect = this._onMobileNewMessageInputSelect.bind(this);
        this._onMobileNewMessageInputSource = this._onMobileNewMessageInputSource.bind(this);

        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
    }

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
     * @returns {mail.messaging.entity.Discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.discuss;
    }

    /**
     * @returns {mail.messaging.entity.MessagingMenu}
     */
    get messagingMenu() {
        return this.env.messaging.messagingMenu;
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
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _useStoreSelector(props) {
        return {
            messagingMenu: this.env.messaging.messagingMenu,
            isDeviceMobile: this.env.messaging.device.isMobile,
            isDiscussOpen: this.env.messaging.discuss.isOpen,
            isMessagingInitialized: this.env.messaging.isInitialized,
        };
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        // in mobile: keeps the messaging menu open in background
        // TODO SEB maybe need to move this to a mobile component?
        if (
            this.env.messaging.device.isMobile &&
            this.env.entities.ChatWindow.hasVisibleChatWindows
        ) {
            return;
        }
        // closes the menu when clicking outside
        if (this.el.contains(ev.target)) {
            return;
        }
        const input = this._mobileNewMessageInputRef.comp;
        if (input && input.contains(ev.target)) {
            return;
        }
        this.messagingMenu.close();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDesktopTabButton(ev) {
        ev.stopPropagation();
        this.messagingMenu.setActiveTabId(ev.currentTarget.dataset.tabId);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickNewMessage(ev) {
        ev.stopPropagation();
        if (!this.env.messaging.device.isMobile) {
            this.env.entities.Thread.openNewMessage();
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
        ev.stopPropagation();
        ev.preventDefault();
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
        const partnerId = ui.item.id;
        const partner = this.env.entities.Partner.fromId(partnerId);
        const chat = partner.directPartnerThread;
        if (chat) {
            chat.open();
        } else {
            this.env.entities.Thread.createChannel({
                autoselect: true,
                partnerId,
                type: 'chat',
            });
        }
        if (!this.env.messaging.device.isMobile) {
            this.messagingMenu.close();
        }
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onMobileNewMessageInputSource(req, res) {
        const value = _.escape(req.term);
        this.env.entities.Partner.imSearch({
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
        this.messagingMenu.setActiveTabId(ev.detail.tabId);
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.thread
     */
    _onSelectThread(ev) {
        ev.stopPropagation();
        this.env.entities.Thread.get(ev.detail.thread).open();
        if (!this.env.messaging.device.isMobile) {
            this.messagingMenu.close();
        }
    }

}

Object.assign(MessagingMenu, {
    components,
    props: {},
    template: 'mail.messaging.component.MessagingMenu',
});

return MessagingMenu;

});
