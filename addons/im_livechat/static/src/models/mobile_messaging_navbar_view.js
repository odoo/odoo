/** @odoo-module **/

import { Patch } from "@mail/model";

Patch({
    name: "MobileMessagingNavbarView",
    fields: {
        tabs: {
            compute() {
                const res = this._super();
                if (this.messaging.pinnedLivechats.length > 0) {
                    return [
                        ...res,
                        {
                            icon: "fa fa-comments",
                            id: "livechat",
                            label: this.env._t("Livechat"),
                        },
                    ];
                }
                return res;
            },
        },
    },
});
