/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
import { luxonToMomentFormat } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "../standard_field_props";

const { Component, onWillStart, useExternalListener, useRef, useEffect } = owl;
const formatters = registry.category("formatters");
const parsers = registry.category("parsers");

export class DateRangeField extends Component {
    setup() {
        this.notification = useService("notification");
        this.root = useRef("root");
        this.isPickerShown = false;
        this.pickerContainer;
        this.momentFormat = luxonToMomentFormat(
            this.isDateTime ? localization.dateTimeFormat : localization.dateFormat
        );

        useExternalListener(window, "scroll", this.onWindowScroll, { capture: true });
        onWillStart(() => loadJS("/web/static/lib/daterangepicker/daterangepicker.js"));
        useEffect(
            (el) => {
                if (el) {
                    const start = this.formattedStartDate;
                    const end = this.formattedEndDate;
                    window.$(el).daterangepicker({
                        timePicker: this.isDateTime,
                        timePicker24Hour: true,
                        timePickerIncrement: 5,
                        autoUpdateInput: false,
                        locale: {
                            applyLabel: this.env._t("Apply"),
                            cancelLabel: this.env._t("Cancel"),
                        },
                        startDate: start ? window.moment(start) : window.moment(),
                        endDate: end ? window.moment(end) : window.moment(),
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
        return this.formatValue(this.props.formatType, this.endDate);
    }
    get formattedStartDate() {
        return this.formatValue(this.props.formatType, this.startDate);
    }
    get startDate() {
        return this.props.record.data[this.props.relatedStartDateField || this.props.name];
    }
    get endDate() {
        return this.props.record.data[this.props.relatedEndDateField || this.props.name];
    }
    get relatedDateRangeField() {
        return this.props.relatedStartDateField
            ? this.props.relatedStartDateField
            : this.props.relatedEndDateField;
    }

    formatValue(format, value) {
        const formatter = formatters.get(format);
        let formattedValue;
        try {
            formattedValue = formatter(value);
        } catch {
            this.props.record.setInvalidField(this.props.name);
        }
        return formattedValue;
    }

    updateRange(start, end) {
        return this.props.record.update({
            [this.props.relatedStartDateField || this.props.name]: start,
            [this.props.relatedEndDateField || this.props.name]: end,
        });
    }

    onChangeInput(ev) {
        const parse = parsers.get(this.props.formatType);
        let value;
        try {
            value = parse(ev.target.value);
        } catch {
            this.props.record.setInvalidField(this.props.name);
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
        const start = this.isDateTime ? picker.startDate : picker.startDate.startOf("day");
        const end = this.isDateTime ? picker.endDate : picker.endDate.startOf("day");
        const parser = parsers.get(this.props.formatType);
        const dates = [start, end].map((date) => {
            return parser(date.format(this.momentFormat));
        });
        await this.updateRange(dates[0], dates[1]);
        const input = document.querySelector(
            `.o_field_daterange[name='${this.relatedDateRangeField}'] input`
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
DateRangeField.props = {
    ...standardFieldProps,
    relatedEndDateField: { type: String, optional: true },
    relatedStartDateField: { type: String, optional: true },
    formatType: { type: String, optional: true },
    placeholder: { type: String, optional: true },
};

DateRangeField.supportedTypes = ["date", "datetime"];

DateRangeField.extractProps = ({ attrs, field }) => {
    return {
        relatedEndDateField: attrs.options.related_end_date,
        relatedStartDateField: attrs.options.related_start_date,
        formatType: attrs.options.format_type || field.type,
        placeholder: attrs.placeholder,
    };
};

registry.category("fields").add("daterange", DateRangeField);
