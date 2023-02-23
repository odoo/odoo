/** @odoo-module **/

import { attr, Model } from "@mail/model";

Model({
    name: "LivechatOperator",
    fields: {
        id: attr({
            identifying: true,
        }),
        name: attr(),
    },
});
