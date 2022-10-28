/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MobileMessagingNavbarView extends Component {

    /**
     * @returns {MobileMessagingNavbarView}
     */
    get mobileMessagingNavbarView() {
        return this.props.record;
    }

}

Object.assign(MobileMessagingNavbarView, {
    props: { record: Object },
    template: 'mail.MobileMessagingNavbarView',
});

registerMessagingComponent(MobileMessagingNavbarView);
