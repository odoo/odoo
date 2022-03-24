/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";

const { Component, onWillStart, useExternalListener, useRef, useEffect } = owl;
const { DateTime } = luxon;

const formatters = registry.category("formatters");

export class DateRangeField extends Component {
    setup() {
        this.root = useRef("root");
        this.isPickerShown = false;

        useExternalListener(window, "scroll", this.onWindowScroll, { capture: true });
        onWillStart(() => loadJS("/web/static/lib/daterangepicker/daterangepicker.js"));
        useEffect(
            (isReadonly) => {
                if (!isReadonly) {
                    window.$(this.root.el).daterangepicker({
                        timePicker: this.isDateTime,
                        timePicker24Hour: true,
                        timePickerIncrement: 5,
                        autoUpdateInput: false,
                        locale: {
                            // applyLabel: this.env._t("Apply"),
                            // cancelLabel: this.env._t("Cancel"),
                            format: this.isDateTime
                                ? localization.dateTimeFormat
                                : localization.dateFormat,
                        },
                        startDate: window.moment(this.formattedStartDate),
                        endDate: window.moment(this.formattedEndDate),
                    });

                    window
                        .$(this.root.el)
                        .on("apply.daterangepicker", this.onPickerApply.bind(this));
                    window.$(this.root.el).on("show.daterangepicker", this.onPickerShow.bind(this));
                    window.$(this.root.el).on("hide.daterangepicker", this.onPickerHide.bind(this));

                    this.pickerContainer.dataset.name = this.props.name;
                }

                return () => {
                    if (!isReadonly) {
                        this.pickerContainer.remove();
                    }
                };
            },
            () => [this.props.readonly]
        );
    }

    get isDateTime() {
        return this.props.formatType === "datetime";
    }

    get formattedValue() {
        return formatters.get(this.props.formatType)(this.props.value, {
            timezone: this.isDateTime,
        });
    }

    get formattedEndDate() {
        return formatters.get(this.props.formatType)(this.props.endDate, {
            timezone: this.isDateTime,
        });
    }

    get formattedStartDate() {
        return formatters.get(this.props.formatType)(this.props.startDate, {
            timezone: this.isDateTime,
        });
    }

    get pickerContainer() {
        return window.$(this.root.el).data("daterangepicker").container[0];
    }

    onWindowScroll(ev) {
        if (this.isPickerShown && !this.env.isSmall && !this.pickerContainer.contains(ev.target)) {
            window.$(this.root.el).data("daterangepicker").hide();
        }
    }

    async onPickerApply(ev, picker) {
        let start = DateTime.fromJSDate(picker.startDate.utc().toDate());
        let end = DateTime.fromJSDate(picker.endDate.utc().toDate());
        if (!this.isDateTime) {
            start = start.startOf("day");
            end = end.startOf("day");
        }
        console.log({
            "picker start": picker.startDate,
            "picker end": picker.endDate,
            "luxon start": start,
            "luxon end": end,
        });
        await this.props.updateRange(start, end);
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
        formatType: attrs.options.format_type || record.fields[fieldName].type,
        endDate: record.data[relatedEndDate || fieldName],
        startDate: record.data[relatedStartDate || fieldName],
        // pickerOptions: attrs.options.datepicker,
        async updateRange(start, end) {
            await Promise.all([
                record.update(relatedStartDate || fieldName, start),
                record.update(relatedEndDate || fieldName, end),
            ]);
        },
    };
};

registry.category("fields").add("daterange", DateRangeField);
