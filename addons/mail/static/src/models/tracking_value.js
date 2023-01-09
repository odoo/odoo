/** @odoo-module **/

import { attr, one, Model } from "@mail/model";
import { sprintf } from "@web/core/utils/strings";

Model({
    name: "TrackingValue",
    fields: {
        /**
         * States the original field of changed tracking value, such as "Status", "Date".
         */
        changedField: attr({ required: true }),
        /**
         * The translated `changedFiled` according to the language setting.
         */
        formattedChangedField: attr({
            compute() {
                return sprintf(this.env._t("%s"), this.changedField);
            },
        }),
        id: attr({ identifying: true }),
        messageOwner: one("Message", { inverse: "trackingValues", readonly: true, required: true }),
        newValue: one("TrackingValueItem", { inverse: "trackingValueAsNewValue" }),
        oldValue: one("TrackingValueItem", { inverse: "trackingValueAsOldValue" }),
    },
});
