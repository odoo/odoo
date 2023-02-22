/** @odoo-module **/

import { formatDateTime } from "@web/core/l10n/dates";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { selectionField, SelectionField } from "../selection/selection_field";

const { DateTime } = luxon;

export class TimezoneMismatchField extends SelectionField {
    static template = "web.TimezoneMismatchField";
    static props = {
        ...super.props,
        tzOffsetField: { type: String, optional: true },
        mismatchTitle: { type: String, optional: true },
    };
    static defaultProps = {
        ...super.defaultProps,
        tzOffsetField: "tz_offset",
        mismatchTitle: _lt(
            "Timezone Mismatch : This timezone is different from that of your browser.\nPlease, set the same timezone as your browser's to avoid time discrepancies in your system."
        ),
    };

    get mismatch() {
        const userOffset = this.props.record.data[this.props.tzOffsetField];
        if (userOffset && this.props.record.data[this.props.name]) {
            const offset = -new Date().getTimezoneOffset();
            let browserOffset = offset < 0 ? "-" : "+";
            browserOffset += _.str.sprintf("%02d", Math.abs(offset / 60));
            browserOffset += _.str.sprintf("%02d", Math.abs(offset % 60));
            return browserOffset !== userOffset;
        } else if (!this.props.record.data[this.props.name]) {
            return true;
        }
        return false;
    }
    get mismatchTitle() {
        if (!this.props.record.data[this.props.name]) {
            return this.env._t("Set a timezone on your user");
        }
        return this.props.mismatchTitle;
    }
    get options() {
        if (!this.mismatch) {
            return super.options;
        }
        return super.options.map((option) => {
            const [value, label] = option;
            if (value === this.props.record.data[this.props.name]) {
                const offset = this.props.record.data[this.props.tzOffsetField].match(
                    /([+-])([0-9]{2})([0-9]{2})/
                );
                const sign = offset[1] === "-" ? -1 : 1;
                const userOffset = sign * (parseInt(offset[2]) * 60 + parseInt(offset[3]));
                const browserOffset = -new Date().getTimezoneOffset();
                // UTC time of the user's selected timezone.
                // E.g.
                // - current time in UTC, say equal to 2021-01-01T00:00:00Z
                // - userOffset of +0300 = 180 minutes
                // - browserOffset of +0200 = -new Date().getTimezoneOffset() = 120 minutes
                // - userUTCDatetime is then 2021-01-01T01:00:00Z
                const userUTCDatetime = DateTime.utc().plus({
                    minutes: userOffset - browserOffset,
                });
                return [value, `${label} (${formatDateTime(userUTCDatetime)})`];
            }
            return [value, label];
        });
    }
}

export const timezoneMismatchField = {
    ...selectionField,
    component: TimezoneMismatchField,
    additionalClasses: ["d-flex"],
    extractProps: (fieldInfo) => ({
        ...selectionField.extractProps(fieldInfo),
        tzOffsetField: fieldInfo.options.tz_offset_field,
        mismatchTitle: fieldInfo.options.mismatch_title,
    }),
};

registry.category("fields").add("timezone_mismatch", timezoneMismatchField);
