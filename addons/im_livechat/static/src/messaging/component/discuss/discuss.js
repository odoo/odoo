odoo.define('im_livechat.messaging.component.Discuss', function (require) {
'use strict';

const components = {
    Discuss: require('mail.messaging.component.Discuss'),
};

const { patch } = require('web.utils');

patch(components.Discuss, 'im_livechat.messaging.component.Discuss', {

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
