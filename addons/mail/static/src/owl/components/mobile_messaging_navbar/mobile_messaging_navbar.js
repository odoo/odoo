odoo.define('mail.component.MobileMessagingNavbar', function (require) {
'use strict';

const { Component } = owl;

class MobileMessagingNavbar extends Component {

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        this.trigger('o-select-mobile-messaging-navbar-tab', {
            tabId: ev.currentTarget.dataset.tabId,
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
