/** @odoo-module **/

import { Discuss } from '@mail/components/discuss/discuss';

import { patch } from 'web.utils';

const components = { Discuss };

patch(components.Discuss.prototype, 'im_livechat/static/src/components/discuss/discuss.js', {

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
