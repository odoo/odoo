odoo.define('mail.component.MessagingMenu', function (require) {
'use strict';

const AutocompleteInput = require('mail.component.AutocompleteInput');
const MobileNavbar = require('mail.component.MobileMessagingNavbar');
const ThreadPreviewList = require('mail.component.ThreadPreviewList');

const { Component } = owl;
const { useDispatch, useGetters, useRef, useStore } = owl.hooks;

class MessagingMenu extends Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.IS_DEV = true;
        /**
         * global JS generated ID for this component. Useful to provide a
         * custom class to autocomplete input, so that click in an autocomplete
         * item is not considered as a click away from messaging menu in mobile.
         */
        this.id = _.uniqueId('o_messagingMenu_');
        this.storeDispatch = useDispatch();
        this.storeGetters = useGetters();
        this.storeProps = useStore(state => {
            return Object.assign({}, state.messagingMenu, {
                counter: this.storeGetters.globalThreadUnreadCounter(),
                isDiscussOpen: state.discuss.isOpen,
                isMobile: state.isMobile,
            });
        });

        /**
         * Reference of the new message input in mobile. Useful to include it
         * and autocomplete menu as "inside" the messaging menu, to prevent
         * closing the messaging menu otherwise.
         */
        this._mobileNewMessageInputRef = useRef('mobileNewMessageInput');

        // bind since passed as props
        this._onMobileNewMessageInputSelect = this._onMobileNewMessageInputSelect.bind(this);
        this._onMobileNewMessageInputSource = this._onMobileNewMessageInputSource.bind(this);

        if (this.IS_DEV) {
            window.messaging_menu = this;
        }
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
    }

    mounted() {
        document.addEventListener('click', this._onClickCaptureGlobal, true);
    }

    willUnmount() {
        document.removeEventListener('click', this._onClickCaptureGlobal, true);
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @return {string}
     */
    get mobileNewMessageInputPlaceholder() {
        return this.env._t("Search user...");
    }

    /**
     * @return {Object[]}
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
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        // in mobile: keeps the messaging menu open in background
        // TODO SEB maybe need to move this to a mobile component?
        if (
            this.storeProps.isMobile &&
            this.storeGetters.haveVisibleChatWindows()
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
        this.storeDispatch('closeMessagingMenu');
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDesktopTabButton(ev) {
        this.storeDispatch('updateMessagingMenu', {
            activeTabId: ev.currentTarget.dataset.tabId,
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickNewMessage(ev) {
        if (!this.storeProps.isMobile) {
            this.storeDispatch('openThread', 'new_message');
            this.storeDispatch('closeMessagingMenu');
        } else {
            this.storeDispatch('toggleMessagingMenuMobileNewMessage');
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickToggler(ev) {
        this.storeDispatch('toggleMessagingMenuOpen');
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onHideMobileNewMessage(ev) {
        ev.stopPropagation();
        this.storeDispatch('toggleMessagingMenuMobileNewMessage');
    }

    /**
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    _onMobileNewMessageInputSelect(ev, ui) {
        // TODO SEB this should probably be done in autocomplete component
        const partnerId = ui.item.id;
        const chat = this.storeGetters.chatFromPartner(`res.partner_${partnerId}`);
        if (chat) {
            this.storeDispatch('openThread', chat.localId);
        } else {
            this.storeDispatch('createChannel', {
                autoselect: true,
                partnerId,
                type: 'chat'
            });
        }
        if (!this.storeProps.isMobile) {
            this.storeDispatch('closeMessagingMenu');
        }
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onMobileNewMessageInputSource(req, res) {
        // TODO SEB this should probably be done in autocomplete component
        const value = _.escape(req.term);
        this.storeDispatch('searchPartners', {
            callback: partners => {
                const suggestions = partners.map(partner => {
                    return {
                        id: partner.id,
                        value: this.storeGetters.partnerName(partner.localId),
                        label: this.storeGetters.partnerName(partner.localId),
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
        this.storeDispatch('updateMessagingMenu', {
            activeTabId: ev.detail.tabId,
        });
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.threadLocalId
     */
    _onSelectThread(ev) {
        this.storeDispatch('openThread', ev.detail.threadLocalId);
        if (!this.storeProps.isMobile) {
            this.storeDispatch('closeMessagingMenu');
        }
    }
}

MessagingMenu.components = {
    AutocompleteInput,
    MobileNavbar,
    ThreadPreviewList,
};

MessagingMenu.template = 'mail.component.MessagingMenu';

return MessagingMenu;

});
