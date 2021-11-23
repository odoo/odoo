/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MobileMessagingNavbar extends Component {

    /**
     * @returns {MobileMessagingNavbarView}
     */
    get mobileMessagingNavbarView() {
        return this.messaging && this.messaging.models['MobileMessagingNavbarView'].get(this.props.mobileMessagingNavbarViewLocalId);
    }

}

Object.assign(MobileMessagingNavbar, {
    props: {
        mobileMessagingNavbarViewLocalId: String,
    },
    template: 'mail.MobileMessagingNavbar',
});

registerMessagingComponent(MobileMessagingNavbar);
