odoo.define('mail.component.MobileMessagingNavbar', function () {
'use strict';

class MobileMessagingNavbar extends owl.Component {

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        const tabId = ev.currentTarget.dataset.tabId;
        this.trigger('o-select-mobile-messaging-navbar-tab', {
            tabId,
        });
    }

}

MobileMessagingNavbar.defaultProps = {
    tabs: [],
};

MobileMessagingNavbar.props = {
    activeTabId: String,
    tabs: {
        type: Array,
        element: {
            type: Object,
            shape: {
                icon: {
                    type: String,
                    optional: true,
                },
                id: String,
                label: String,
            },
        },
    },
};

MobileMessagingNavbar.template = 'mail.component.MobileMessagingNavbar';

return MobileMessagingNavbar;

});
