/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart, useExternalListener, useRef, useEffect } = owl;
const formatters = registry.category("formatters");
const parsers = registry.category("parsers");

export class DateRangeField extends Component {
    setup() {
        this.notification = useService("notification");
        this.root = useRef("root");
        this.isPickerShown = false;
        this.pickerContainer;

        useExternalListener(window, "scroll", this.onWindowScroll, { capture: true });
        onWillStart(() => loadJS("/web/static/lib/daterangepicker/daterangepicker.js"));
        useEffect(
            (el) => {
                if (el) {
                    window.$(el).daterangepicker({
                        timePicker: this.isDateTime,
                        timePicker24Hour: true,
                        timePickerIncrement: 5,
                        autoUpdateInput: false,
                        locale: {
                            applyLabel: this.env._t("Apply"),
                            cancelLabel: this.env._t("Cancel"),
                            format: this.isDateTime
                                ? localization.dateTimeFormat
                                : localization.dateFormat,
                        },
                        startDate: window.moment(this.formattedStartDate),
                        endDate: window.moment(this.formattedEndDate),
                    });
                    this.pickerContainer = window.$(el).data("daterangepicker").container[0];

                    window.$(el).on("apply.daterangepicker", this.onPickerApply.bind(this));
                    window.$(el).on("show.daterangepicker", this.onPickerShow.bind(this));
                    window.$(el).on("hide.daterangepicker", this.onPickerHide.bind(this));

                    this.pickerContainer.dataset.name = this.props.name;
                }

                return () => {
                    if (el) {
                        this.pickerContainer.remove();
                    }
                };
            },
            () => [this.root.el]
        );
    }

    get isDateTime() {
        return this.props.formatType === "datetime";
    }
    get formattedValue() {
        return this.formatValue(this.props.formatType, this.props.value);
    }

    get formattedEndDate() {
        return this.formatValue(this.props.formatType, this.props.endDate);
    }

    get formattedStartDate() {
        return this.formatValue(this.props.formatType, this.props.startDate);
    }

    formatValue(format, value) {
        const formatter = formatters.get(format);
        let formattedValue;
        try {
            formattedValue = formatter(value, { timezone: this.isDateTime });
        } catch {
            this.props.invalidate();
        }
        return formattedValue;
    }

    onChangeInput(ev) {
        const parse = parsers.get(this.props.formatType);
        let value;
        try {
            value = parse(ev.target.value, { timezone: this.isDateTime });
        } catch {
            this.props.invalidate();
            return;
        }
        this.props.update(value);
    }

    onWindowScroll(ev) {
        const target = ev.target;
        if (
            this.isPickerShown &&
            !this.env.isSmall &&
            (target === window || !this.pickerContainer.contains(target))
        ) {
            window.$(this.root.el).data("daterangepicker").hide();
        }
    }

    async onPickerApply(ev, picker) {
        let start = this.isDateTime ? picker.startDate : picker.startDate.startOf("day");
        let end = this.isDateTime ? picker.endDate : picker.endDate.startOf("day");
        const format = this.isDateTime ? localization.dateTimeFormat : localization.dateFormat;
        const parser = parsers.get(this.props.formatType);
        const dates = [start, end].map((date) => {
            return parser(date.format(format.toUpperCase()), {
                timezone: this.isDateTime,
            });
        });
        await this.props.updateRange(dates[0], dates[1]);
        const input = document.querySelector(
            `.o_field_daterange[name='${this.props.relatedDateRange}'] input`
        );
        const target = window.$(input).data("daterangepicker");
        target.setStartDate(picker.startDate);
        target.setEndDate(picker.endDate);
    }
    onPickerShow() {
        this.isPickerShown = true;
    }
    onPickerHide() {
        this.isPickerShown = false;
    }
}
DateRangeField.template = "web.DateRangeField";

DateRangeField.supportedTypes = ["date", "datetime"];

DateRangeField.extractProps = (fieldName, record, attrs) => {
    const relatedEndDate = attrs.options.related_end_date;
    const relatedStartDate = attrs.options.related_start_date;

    return {
        relatedDateRange: relatedEndDate ? relatedEndDate : relatedStartDate,
        endDate: record.data[relatedEndDate || fieldName],
        formatType: attrs.options.format_type || record.fields[fieldName].type,
        invalidate: () => record.setInvalidField(fieldName),
        startDate: record.data[relatedStartDate || fieldName],
        async updateRange(start, end) {
            await record.update({
                [relatedStartDate || fieldName]: start,
                [relatedEndDate || fieldName]: end,
            });
        },
    };
};

registry.category("fields").add("daterange", DateRangeField);
