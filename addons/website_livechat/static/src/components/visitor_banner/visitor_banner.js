odoo.define('website_livechat/static/src/components/visitor_banner/visitor_banner.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class VisitorBanner extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const visitor = this.env.models['website_livechat.visitor'].get(props.visitorLocalId);
            const country = visitor && visitor.country;
            return {
                country: country && country.__state,
                visitor: visitor ? visitor.__state : undefined,
            };
        });
    }

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

return VisitorBanner;

});
