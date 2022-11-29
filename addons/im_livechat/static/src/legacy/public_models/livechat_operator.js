/** @odoo-module **/

import { attr, Model } from "@im_livechat/legacy/model";

Model({
    name: "LivechatOperator",
    fields: {
        id: attr({
            identifying: true,
        }),
        name: attr(),
    },
});
