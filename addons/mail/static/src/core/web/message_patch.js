/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { markEventHandled } from "@mail/utils/common/misc";

import { getCurrency } from "@web/core/currency";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { format } from "web.field_utils";

const formatters = registry.category("formatters");

patch(Message.prototype, "mail/core/web", {
    setup() {
        this._super(...arguments);
        this.action = useService("action");
    },
    get authorText() {
        return this.hasAuthorClickable ? _t("Open profile") : undefined;
    },
    get hasAuthorClickable() {
        return this.message.author && !this.message.isSelfAuthored;
    },
    onClickAuthor(ev) {
        if (this.hasAuthorClickable) {
            markEventHandled(ev, "Message.ClickAuthor");
            this.messaging.openDocument({
                model: "res.partner",
                id: this.message.author.id,
            });
        }
    },
    openRecord() {
        if (this.message.resModel === "discuss.channel") {
            this.threadService.open(this.message.originThread);
        } else {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_id: this.message.resId,
                res_model: this.message.resModel,
                views: [[false, "form"]],
            });
        }
    },

    /**
     * @returns {string}
     */
    formatTracking(trackingValue) {
        /**
         * Maps tracked field type to a JS formatter. Tracking values are
         * not always stored in the same field type as their origin type.
         * Field types that are not listed here are not supported by
         * tracking in Python. Also see `create_tracking_values` in Python.
         */
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
                return format.char(trackingValue.value);
            case "date":
                if (trackingValue.value) {
                    return luxon.DateTime.fromISO(trackingValue.value, { setZone: "utc" }).toFormat(
                        "LL/dd/yyyy"
                    );
                }
                return format.date(trackingValue.value);
            case "datetime": {
                const value = trackingValue.value
                    ? deserializeDateTime(trackingValue.value)
                    : trackingValue.value;
                return formatters.get("datetime")(value);
            }
            case "float":
                return format.float(trackingValue.value);
            case "integer":
                return format.integer(trackingValue.value);
            case "text":
                return format.text(trackingValue.value);
            case "monetary":
                return format.monetary(trackingValue.value, undefined, {
                    currency: trackingValue.currencyId
                        ? getCurrency(trackingValue.currencyId)
                        : undefined,
                    forceString: true,
                });
            default:
                return trackingValue.value;
        }
    },

    /**
     * @returns {string}
     */
    formatTrackingOrNone(trackingValue) {
        const formattedValue = this.formatTracking(trackingValue);
        return formattedValue || _t("None");
    },
});
