odoo.define('website_livechat/static/src/components/visitor_banner/visitor_banner.js', function (require) {
'use strict';

const { registerMessagingComponent } = require('@mail/utils/messaging_component');

const { Component } = owl;

class VisitorBanner extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {website_livechat.visitor}
     */
    get visitor() {
        return this.env.models['website_livechat.visitor'].get(this.props.visitorLocalId);
    }

}

Object.assign(VisitorBanner, {
    props: {
        visitorLocalId: String,
    },
    template: 'website_livechat.VisitorBanner',
});

registerMessagingComponent(VisitorBanner);

return VisitorBanner;

});
