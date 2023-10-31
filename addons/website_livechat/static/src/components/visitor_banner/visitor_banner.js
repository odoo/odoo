/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class VisitorBanner extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {website_livechat.visitor}
     */
    get visitor() {
        return this.messaging && this.messaging.models['website_livechat.visitor'].get(this.props.visitorLocalId);
    }

}

Object.assign(VisitorBanner, {
    props: {
        visitorLocalId: String,
    },
    template: 'website_livechat.VisitorBanner',
});

registerMessagingComponent(VisitorBanner);

export default VisitorBanner;
