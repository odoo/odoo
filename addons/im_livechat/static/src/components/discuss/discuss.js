odoo.define('im_livechat/static/src/components/discuss/discuss.js', function (require) {
'use strict';

const components = {
    Discuss: require('mail/static/src/components/discuss/discuss.js'),
};

const { patch } = require('web.utils');

patch(components.Discuss, 'im_livechat/static/src/components/discuss/discuss.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    mobileNavbarTabs(...args) {
        return [...this._super(...args), {
            icon: 'fa fa-comments',
            id: 'livechat',
            label: this.env._t("Livechat"),
        }];
    }

});

});
