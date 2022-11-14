/** @odoo-module **/

import { one, Patch } from "@mail/model";

Patch({
    name: "ClockWatcher",
    fields: {
        qunitTestOwner: one("QUnitTest", {
            identifying: true,
            inverse: "clockWatcher",
        }),
    },
});
