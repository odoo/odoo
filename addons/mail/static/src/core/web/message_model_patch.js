import { Message } from "@mail/core/common/message_model";

import {
    deserializeDate,
    deserializeDateTime,
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { formatFloat } from "@web/core/utils/numbers";
import { patch } from "@web/core/utils/patch";
import {
    formatChar,
    formatInteger,
    formatMonetary,
    formatText,
} from "@web/views/fields/formatters";

patch(Message.prototype, {
    /**
     * @returns {string}
     */
    formatTracking(trackingType, trackingValue) {
        switch (trackingType) {
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
            case "date": {
                const value = trackingValue.value
                    ? deserializeDate(trackingValue.value)
                    : trackingValue.value;
                return formatDate(value);
            }
            case "datetime": {
                const value = trackingValue.value
                    ? deserializeDateTime(trackingValue.value)
                    : trackingValue.value;
                return formatDateTime(value);
            }
            case "float":
                return formatFloat(trackingValue.value);
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
    formatTrackingOrNone(trackingType, trackingValue) {
        const formattedValue = this.formatTracking(trackingType, trackingValue);
        return formattedValue || _t("None");
    },

    /**
     * @returns {string}
     */
    generateTrackingMessage() {
        const returnLine = "\n";
        if (!this.trackingValues.length) {
            return "";
        }
        let trackingMessage = "";
        if (this.subtype_description) {
            trackingMessage = returnLine + this.subtype_description + returnLine;
        }
        for (const trackingValue of this.trackingValues) {
            const oldValue = this.formatTrackingOrNone(
                trackingValue.fieldType,
                trackingValue.oldValue
            );
            const newValue = this.formatTrackingOrNone(
                trackingValue.fieldType,
                trackingValue.newValue
            );
            trackingMessage += `${trackingValue.changedField}: ${oldValue}`;
            if (oldValue !== newValue) {
                trackingMessage += ` → ${newValue}`;
            }
            trackingMessage += returnLine;
        }
        return trackingMessage;
    },
});
