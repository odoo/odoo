/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { markEventHandled } from "@web/core/utils/misc";

import { deserializeDateTime, formatDate, formatDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import {
    formatChar,
    formatInteger,
    formatMonetary,
    formatText,
} from "@web/views/fields/formatters";
import { formatFloat } from "@web/core/utils/numbers";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.userService = useService("user");
        this.messaging = useState(useService("mail.messaging"));
    },
    get authorAvatarAttClass() {
        return {
            ...super.authorAvatarAttClass,
            "o_redirect cursor-pointer": this.hasAuthorClickable,
        };
    },
    getAuthorText() {
        return this.hasAuthorClickable() ? _t("Open profile") : undefined;
    },
    hasAuthorClickable() {
        return this.message.author && !this.message.isSelfAuthored;
    },
    onClickAuthor(ev) {
        if (this.hasAuthorClickable()) {
            markEventHandled(ev, "Message.ClickAuthor");
            this.messaging.openDocument({
                model: "res.partner",
                id: this.message.author.id,
            });
        }
    },
    openRecord() {
        this.threadService.open(this.message.originThread);
    },

    /**
     * @returns {string}
     */
    formatTracking(trackingValue, fieldName) {
        /**
         * Maps tracked field type to a JS formatter. Tracking values are
         * not always stored in the same field type as their origin type.
         * Field types that are not listed here are not supported by
         * tracking in Python. Also see `create_tracking_values` in Python.
         */
        let modelDigits = 0;
        switch (trackingValue.fieldType) {
            case "boolean":
                return trackingValue.value ? _t("Yes") : _t("No");
            /**
             * many2one formatter exists but is expecting id/display_name or data
             * object but only the target record name is known in this context.
             *
             * Selection formatter exists but requires knowing all
             * possibilities and they are not given in this context.
             */
            case "char":
            case "many2one":
            case "selection":
                return formatChar(trackingValue.value);
            case "date":
                if (trackingValue.value) {
                    return luxon.DateTime.fromISO(trackingValue.value, { zone: "utc" })
                        .setZone("system")
                        .toLocaleString({ locale: this.userService.lang.replace("_", "-") });
                }
                return formatDate(trackingValue.value);
            case "datetime": {
                const value = trackingValue.value
                    ? deserializeDateTime(trackingValue.value)
                    : trackingValue.value;
                return formatDateTime(value);
            }
            case "float":
                if (fieldName) {
                    // POC 2: (it's not there yet)
                    // Ideally it should use the digits spec from the view, not the model
                    // but unfortunately those are props of the FloatField, and not accessible by this component.
                    // We may want to store 16 decimals in the db, but only display 8 on the view
                    // The tracking values should therefore match the same value as the view
                    // I have used [12,7] on the field, and [12,6] in the view to illustrate this.
                    //
                    // Crazy Idea/ Joke: maybe the formCompiler override in mail should compile a list of float fields
                    // along with their info/spec and make it accessible to Chatter -> Thread -> Message
                    // seems like a lot of complexity for a small use case.
                    //
                    // The simplest option is to display 2 decimals in the chatter with a t-att-title containing the db
                    // value - To check with PO
                    modelDigits = this.env.model.root.fields[fieldName]?.digits;
                }
                return formatFloat(trackingValue.value, { digits: modelDigits });
            case "integer":
                return formatInteger(trackingValue.value);
            case "text":
                return formatText(trackingValue.value);
            case "monetary":
                return formatMonetary(trackingValue.value, {
                    currencyId: trackingValue.currencyId,
                });
            default:
                return trackingValue.value;
        }
    },

    /**
     * @returns {string}
     */
    formatTrackingOrNone(trackingValue, fieldName) {
        const formattedValue = this.formatTracking(trackingValue, fieldName);
        return formattedValue || _t("None");
    },
});
