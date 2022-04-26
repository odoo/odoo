/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MobileMessagingNavbarTab extends Component {

    /**
     * @returns {MobileMessagingNavbarView}
     */
    get mobileMessagingNavbarView() {
        return this.messaging && this.messaging.models['MobileMessagingNavbarView'].get(this.props.mobileMessagingNavbarViewLocalId);
    }

}

Object.assign(MobileMessagingNavbarTab, {
    props: {
        mobileMessagingNavbarViewLocalId: String,
        tab: Object,
    },
    template: 'mail.MobileMessagingNavbarTab',
});

registerMessagingComponent(MobileMessagingNavbarTab);
