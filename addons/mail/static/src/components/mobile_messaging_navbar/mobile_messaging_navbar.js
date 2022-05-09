/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MobileMessagingNavbar extends Component {

    /**
     * @returns {MobileMessagingNavbarView}
     */
    get mobileMessagingNavbarView() {
        return this.props.record;
    }

}

Object.assign(MobileMessagingNavbar, {
    props: { record: Object },
    template: 'mail.MobileMessagingNavbar',
});

registerMessagingComponent(MobileMessagingNavbar);
