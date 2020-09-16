odoo.define('website_livechat/static/src/components/discuss/discuss.js', function (require) {
'use strict';

const components = {
    Discuss: require('mail/static/src/components/discuss/discuss.js'),
    VisitorBanner: require('website_livechat/static/src/components/visitor_banner/visitor_banner.js'),
};

Object.assign(components.Discuss.components, {
    VisitorBanner: components.VisitorBanner,
});

});
