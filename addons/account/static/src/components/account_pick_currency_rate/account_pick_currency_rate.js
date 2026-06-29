import { Component, proxy, props, types as t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { useService } from "@web/core/utils/hooks";
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
                };
            },
        });
    }
}

export class AccountCurrencyExchangeRate extends Component {
    static template = "account.AccountCurrencyExchangeRate";
    props = props({
        readonly: t.boolean(),
        record: t.object(),
        rateField: t.string(),
    });

    setup() {
        this._swapKey = "account.currency_exchange_rate.swapped";
        this.state = proxy({
            swapped: localStorage.getItem(this._swapKey) === "true" 
        });
    }

    get rate() {
        return this.props.record.data[this.props.rateField];
    }

    get fromCurrency() {
        return this.state.swapped
            ? this.props.record.data.currency_id
            : this.props.record.data.company_currency_id;
    }

    get toCurrency() {
        return this.state.swapped
            ? this.props.record.data.company_currency_id
            : this.props.record.data.currency_id;
    }

    get displayRate() {
        if (!this.rate) {
            return "0.000000";
        }
        return (this.state.swapped ? 1 / this.rate : this.rate).toFixed(6);
    }

    get isEditable() {
        return !this.props.readonly;
    }

    onSwap() {
        this.state.swapped = !this.state.swapped;
        localStorage.setItem(this._swapKey, this.state.swapped);
    }

    async onRateInput(ev) {
        const parsed = parseFloat(ev.target.value.replace(",", "."));
        if (isNaN(parsed) || parsed <= 0) {
            ev.target.value = this.displayRate;
            return;
        }
        const newRate = this.state.swapped ? 1 / parsed : parsed;
        await this.props.record.update({ [this.props.rateField]: newRate });
    }
}

export const accountPickCurrencyDate = {
    component: AccountPickCurrencyDate,
}

export const accountCurrencyExchangeRate = {
    component: AccountCurrencyExchangeRate,
    extractProps: ({ options }) => ({
        rateField: options.rate_field,
    }),
};

registry.category("view_widgets").add("account_pick_currency_date",  accountPickCurrencyDate);
registry.category("view_widgets").add("account_currency_exchange_rate", accountCurrencyExchangeRate);
