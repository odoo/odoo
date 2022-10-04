/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'MobileMessagingNavbarView',
    fields: {
        tabs: {
            compute() {
                const res = this._super();
                if (this.global.Messaging.pinnedLivechats.length > 0) {
                    return [...res, {
                        icon: 'fa fa-comments',
                        id: 'livechat',
                        label: this.env._t("Livechat"),
                    }];
                }
                return res;
            },
        },
    },
});
