/** @odoo-module **/

import { attr, clear, one, Model } from "@mail/model";

import { sprintf } from "@web/core/utils/strings";

Model({
    name: "CallSystrayMenu",
    template: "mail.CallSystrayMenu",
    fields: {
        buttonTitle: attr({
            default: "",
            compute() {
                if (!this.messaging.rtc.channel) {
                    return clear();
                }
                return sprintf(
                    this.env._t("Open conference: %s"),
                    this.messaging.rtc.channel.displayName
                );
            },
        }),
        rtc: one("Rtc", { identifying: true, inverse: "callSystrayMenu" }),
    },
});
