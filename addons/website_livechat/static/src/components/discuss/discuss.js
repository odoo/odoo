odoo.define('website_livechat/static/src/components/discuss/discuss.js', function (require) {
'use strict';

const components = {
    Discuss: require('mail/static/src/components/discuss/discuss.js'),
    VisitorBanner: require('website_livechat/static/src/components/visitor_banner/visitor_banner.js'),
};

components.Discuss.patch('website_livechat/static/src/components/discuss/discuss.js', T =>
    class extends T {

        /**
         * @override
         */
        _useStoreSelector(props) {
            const res = super._useStoreSelector(...arguments);
            const thread = res.thread;
            const visitor = thread && thread.visitor;
            return Object.assign({}, res, {
                visitor,
            });
        }

    }
);

Object.assign(components.Discuss.components, {
    VisitorBanner: components.VisitorBanner,
});

});
