/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MobileMessagingNavbar extends Component {

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

registerMessagingComponent(MobileMessagingNavbar, { propsCompareDepth: { tabs: 2 } });
