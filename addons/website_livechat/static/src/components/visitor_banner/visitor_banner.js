odoo.define('website_livechat/static/src/components/visitor_banner/visitor_banner.js', function (require) {
'use strict';

const { useModels } = require('@mail/component_hooks/use_models/use_models');
const { useShouldUpdateBasedOnProps } = require('@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props');

const { Component } = owl;

class VisitorBanner extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
        useShouldUpdateBasedOnProps();
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
