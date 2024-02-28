/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class VisitorBanner extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Visitor}
     */
    get visitor() {
        return this.props.visitor;
    }

}

Object.assign(VisitorBanner, {
    props: { visitor: Object },
    template: 'website_livechat.VisitorBanner',
});

registerMessagingComponent(VisitorBanner);

export default VisitorBanner;
