/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core_ui/message";
import { useService } from "@web/core/utils/hooks";
import { format } from "web.field_utils";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { getCurrency } from "@web/core/currency";

const formatters = registry.category("formatters");

patch(Message.prototype, "mail/web", {
    setup() {
        this._super(...arguments);
        this.action = useService("action");
        this.userService = useService("user");
    },

    onClickAuthor(ev) {
        if (this.message.author && this.hasAuthorClickable && !this.hasOpenChatFeature) {
            this.messaging.openDocument({
                model: "res.partner",
                id: this.message.author.id,
            });
            return;
        }
        return this._super(ev);
    },

    get authorText() {
        return this.hasAuthorClickable && !this.hasOpenChatFeature
            ? _t("Open profile")
            : this._super();
    },

    openRecord() {
        this.threadService.open(this.message.originThread);
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
             * many2one formatter exists but is expecting id/name_get or data
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
                    return luxon.DateTime.fromISO(trackingValue.value, { zone: "utc" })
                        .setZone("system")
                        .toLocaleString({ locale: this.userService.lang.replace("_", "-") });
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
