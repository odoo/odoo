odoo.define('website_livechat/static/src/components/discuss/discuss.js', function (require) {
'use strict';

const components = {
    Discuss: require('@mail/components/discuss/discuss')[Symbol.for("default")],
    VisitorBanner: require('website_livechat/static/src/components/visitor_banner/visitor_banner.js'),
};
const { patch } = require('web.utils');

patch(components.Discuss.prototype, 'website_livechat/static/src/components/discuss/discuss.js', {

    /**
     * @override
     */
    _useStoreSelector(props) {
        const res = this._super(...arguments);
        const thread = res.thread;
        const visitor = thread && thread.visitor;
        return Object.assign({}, res, {
            visitor,
        });
    },

});

Object.assign(components.Discuss.components, {
    VisitorBanner: components.VisitorBanner,
});

});
