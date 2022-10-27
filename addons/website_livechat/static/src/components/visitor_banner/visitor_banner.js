/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class VisitorBannerView extends Component {

    /**
     * @returns {VisitorBannerView}
     */
    get visitorBannerView() {
        return this.props.record;
    }

}

Object.assign(VisitorBannerView, {
    props: { record: Object },
    template: 'website_livechat.VisitorBannerView',
});

registerMessagingComponent(VisitorBannerView);
