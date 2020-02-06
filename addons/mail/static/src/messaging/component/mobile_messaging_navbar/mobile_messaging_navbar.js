odoo.define('mail.messaging.component.MobileMessagingNavbar', function (require) {
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

Object.assign(MobileMessagingNavbar, {
    defaultProps: {
        tabs: [],
    },
    props: {
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
    },
    template: 'mail.messaging.component.MobileMessagingNavbar',
});

return MobileMessagingNavbar;

});
