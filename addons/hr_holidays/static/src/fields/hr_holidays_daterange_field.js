import { registry } from "@web/core/registry";
import { DateTimeField, dateRangeField } from "@web/views/fields/datetime/datetime_field";
import { _t } from "@web/core/l10n/translation";
import { useRef,useEffect } from "@odoo/owl";

export class HrHolidaysDateTimeField extends DateTimeField {
    static template = "hr_holidays.HrHolidaysDateTimeField";
    static props = {
        ...DateTimeField.props,
        startPeriodField: { type: String, optional: true },
        endPeriodField: { type: String, optional: true },
    }
    setup(){
        super.setup()
        // debugger;
        console.log("props :", this.props)
        this.endPeriod = useRef("end-period")
        this.startPeriod = useRef("start-period")
        useEffect(
            () => {
                [this.endPeriod, this.startPeriod].forEach((ref, index) => {
                    console.log("endPeriodField :", this.endPeriodField)
                    // if (ref.el?.getAttribute("data-field") === this.picker.activeInput) {
                    //     ref.el.focus();
                    //     this.openPicker(index);
                    // }
                });
            },
            () => [this.endPeriod.el?.tagName, this.endPeriod.el?.tagName]
        );

    }
    get endPeriodField(){
        console.log("Helloowwwewe")
        console.log(this.props.endPeriodField)
        return this.props.endPeriodField || null;
    }
    
    shouldShowSeparator() {
        return !this.isEmpty(this.endDateField) && super.shouldShowSeparator();
    }
}

const START_PERIOD_FIELD_OPTION = "start_period_field";
const END_PERIOD_FIELD_OPTION = "end_period_field";

export const hrHolidaysDateRangeField = {
    ...dateRangeField,
    component: HrHolidaysDateTimeField,
    supportedOptions: [
        ...dateRangeField.supportedOptions,
        {
            label: _t("Start period field"),
            name: START_PERIOD_FIELD_OPTION,
            type: "selection",
        },
        {
            label: _t("End period field"),
            name: END_PERIOD_FIELD_OPTION,
            type: "selection",
        },
    ],
    extractProps: ({ attrs, options, placeholder, type }, dynamicInfo) => {
        console.log("Hello World ...")
        console.log(options)
        return {
            ...dateRangeField.extractProps({ attrs, options, placeholder, type }, dynamicInfo),
            startPeriodField: options[START_PERIOD_FIELD_OPTION],
            endPeriodField: options[END_PERIOD_FIELD_OPTION],
        };
    },
};

registry.category("fields").add("hr_holidays_daterange", hrHolidaysDateRangeField);