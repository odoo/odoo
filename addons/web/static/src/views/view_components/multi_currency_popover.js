import { Component, onWillStart, useExternalListener, useState } from "@odoo/owl";
import { getCurrency, getCurrencyRates } from "@web/core/currency";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { formatMonetary } from "../fields/formatters";

export class MultiCurrencyPopover extends Component {
    static template = "web.MultiCurrencyPopover";
    static props = {
        close: Function,
        currencyIds: Array,
        target: HTMLElement,
        value: Number,
    };

    setup() {
        this.orm = useService("orm");
        this.defaultCurrency = user.activeCompany.currency_id;
        this.state = useState({ rates: null });
        onWillStart(async () => {
            this.state.rates = await getCurrencyRates();
        });
        useExternalListener(window, "mouseover", (ev) => {
            if (ev.target !== this.props.target) {
                this.props.close();
            }
        });
    }

    get currencies() {
        return this.props.currencyIds.reduce((currencies, currencyId) => {
            if (currencyId !== this.defaultCurrency) {
                currencies.push({
                    ...getCurrency(currencyId),
                    id: currencyId,
                    rate: this.state.rates[currencyId],
                    value: this.props.value / this.state.rates[currencyId],
                });
            }
            return currencies;
        }, []);
    }

    formatedValue(value, currencyId) {
        return formatMonetary(value, { currencyId });
    }
}
