/** @odoo-module **/

import { attr, Model } from "@mail/legacy/model";

Model({
    name: "LivechatOperator",
    fields: {
        id: attr({
            identifying: true,
        }),
        name: attr(),
    },
});
