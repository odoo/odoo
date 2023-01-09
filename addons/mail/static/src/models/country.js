/** @odoo-module **/

import { attr, clear, Model } from "@mail/model";

Model({
    name: "Country",
    fields: {
        code: attr(),
        flagUrl: attr({
            compute() {
                if (!this.code) {
                    return clear();
                }
                return `/base/static/img/country_flags/${this.code}.png`;
            },
        }),
        id: attr({ identifying: true }),
        name: attr(),
    },
});
