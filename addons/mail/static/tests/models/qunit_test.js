/** @odoo-module **/

import { one, Model } from "@mail/model";

Model({
    name: "QUnitTest",
    fields: {
        clockWatcher: one("ClockWatcher", {
            inverse: "qunitTestOwner",
        }),
        throttle1: one("Throttle", {
            inverse: "qunitTestOwner1",
        }),
        throttle2: one("Throttle", {
            inverse: "qunitTestOwner2",
        }),
        timer1: one("Timer", {
            inverse: "qunitTestOwner1",
        }),
        timer2: one("Timer", {
            inverse: "qunitTestOwner2",
        }),
    },
});
