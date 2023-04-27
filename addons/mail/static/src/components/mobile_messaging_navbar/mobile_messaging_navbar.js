odoo.define('mail/static/src/components/mobile_messaging_navbar/mobile_messaging_navbar.js', function (require) {
'use strict';

const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');

const { Component } = owl;

class MobileMessagingNavbar extends Component {

    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps({
            compareDepth: {
                tabs: 2,
            },
        });
    }

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
    template: 'mail.MobileMessagingNavbar',
});

return MobileMessagingNavbar;

});
