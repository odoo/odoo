import { render } from "@web/owl2/utils";
import { Component, signal } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { formatDate } from "@web/core/l10n/dates";

export class StockValuationReportFilters extends Component {
    static template = "account.StockValuationReport.Filters";
    static props = {};

    dateFilterRef = signal.ref();

    setup() {
        const getPickerProps = () => {
            const pickerProps = {
                value: this.env.controller.state.date,
                type: "date",
            };
            return pickerProps;
        };
        this.dateTimePicker = useDateTimePicker({
            target: this.dateFilterRef,
            get pickerProps() {
                return getPickerProps();
            },
            onApply: (newDate) => {
                if (newDate) {
                    this.env.controller.setDate(newDate);
                    render(this);
                }
            },
        });
    }

    onDateClick() {
        this.dateTimePicker.open();
    }

    get date() {
        return formatDate(this.env.controller.state.date);
    }
}
