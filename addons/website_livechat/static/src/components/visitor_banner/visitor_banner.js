/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class VisitorBanner extends Component {

    /**
     * @returns {VisitorBannerView}
     */
    get visitorBannerView() {
        return this.props.record;
    }

}

Object.assign(VisitorBanner, {
    props: { record: Object },
    template: 'website_livechat.VisitorBanner',
});

registerMessagingComponent(VisitorBanner);
