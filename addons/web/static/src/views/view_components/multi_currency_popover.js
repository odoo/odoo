// @ts-check

/** @module @web/views/view_components/multi_currency_popover - Popover showing a monetary value converted into each active company currency */

import { Component, onWillStart, useExternalListener, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { formatMonetary } from "@web/fields/formatters";
import { getCurrency, getCurrencyRates } from "@web/services/currency";
import { user } from "@web/services/user";

/** Popover showing a monetary value converted into each of the company's active currencies. */
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

    /** @returns {Array<Object>} non-default currencies with their rates and converted values */
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

    /**
     * @param {number} value
     * @param {number} currencyId
     * @returns {string} formatted monetary string
     */
    formatedValue(value, currencyId) {
        return formatMonetary(value, { currencyId });
    }
}
