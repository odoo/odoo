odoo.define('website_livechat/static/src/components/discuss/discuss.js', function (require) {
'use strict';

const { Discuss } = require('@mail/components/discuss/discuss');

const components = {
    Discuss,
    VisitorBanner: require('website_livechat/static/src/components/visitor_banner/visitor_banner.js'),
};

Object.assign(components.Discuss.components, {
    VisitorBanner: components.VisitorBanner,
});

});
