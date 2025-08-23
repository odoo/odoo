import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { useService } from "@web/core/utils/hooks";
import { today } from "@web/core/l10n/dates";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";


export class AccountPickCurrencyDate extends Component {
    static template = "account.AccountPickCurrencyDate";
    static props = {
        ...standardWidgetProps,
        record: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.dateTimePicker = useDateTimePicker({
            target: 'datetime-picker-target',
            onApply: async (date) => {
                const record = this.props.record
                const rate = await this.orm.call(
                    'account.move',
                    'get_currency_rate',
                    [record.resId, record.data.company_id.id, record.data.currency_id.id, date.toISODate()],
                );
                this.props.record.update({ invoice_currency_rate: rate });
                await this.props.record.save();
            },
            get pickerProps() {
                return {
                    type: 'date',
                    value: today(),
                };
            },
        });
    }
}

export const accountPickCurrencyDate = {
    component: AccountPickCurrencyDate,
}

registry.category("view_widgets").add("account_pick_currency_date",  accountPickCurrencyDate);
