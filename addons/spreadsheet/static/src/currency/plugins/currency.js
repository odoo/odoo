/** @odoo-module */

import { CellErrorType, helpers, registries } from "@odoo/o-spreadsheet";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { toServerDateString } from "@spreadsheet/helpers/helpers";
import { _t } from "@web/core/l10n/translation";
const { featurePluginRegistry } = registries;
const { createCurrencyFormat } = helpers;

/**
 * @typedef Currency
 * @property {string} name
 * @property {string} code
 * @property {string} symbol
 * @property {number} decimalPlaces
 * @property {"before" | "after"} position
 */

/**
 * @template T
 * @typedef {import("@spreadsheet/data_sources/loadable").Loadable} Loadable<T>
 */

export class CurrencyPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ ([
        "getCurrencyRate",
        "computeFormatFromCurrency",
        "getCompanyCurrencyFormat",
    ]);

    constructor(config) {
        super(config);
        /** @type {string | undefined} */
        this.currentCompanyCurrencyFormat = config.defaultCurrencyFormat;
        /** @type {import("@spreadsheet/data_sources/server_data").ServerData} */
        this._serverData = config.custom.odooDataProvider?.serverData;
    }

    get serverData() {
        if (!this._serverData) {
            throw new Error(
                "'serverData' is not defined, please make sure a 'OdooDataProvider' instance is provided to the model."
            );
        }
        return this._serverData;
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    /**
     * Get the currency rate between the two given currencies
     * @param {string} from Currency from
     * @param {string} to Currency to
     * @param {string} date
     * @returns {{ value: number|false}}
     */
    getCurrencyRate(from, to, date) {
        const rate = this.serverData.batch
            .get("res.currency.rate", "get_rates_for_spreadsheet", {
                from,
                to,
                date: date ? toServerDateString(date) : undefined,
            })
            .toEvaluationValue("rate");
        if (rate.value === false) {
            {
                return {
                    value: CellErrorType.GenericError, // change to #N/A?
                    message: _t("Currency rate unavailable."),
                };
            }
        }
        return rate;
    }

    /**
     * @param {Currency | undefined} currency
     * @returns {string | undefined}
     */
    computeFormatFromCurrency(currency) {
        if (!currency) {
            return undefined;
        }
        return createCurrencyFormat({
            symbol: currency.symbol,
            position: currency.position,
            decimalPlaces: currency.decimalPlaces,
        });
    }

    /**
     * Returns the default display format of a the company currency
     * @param {number} [companyId]
     * @returns {Loadable<string> | string | undefined}
     */
    getCompanyCurrencyFormat(companyId) {
        if (!companyId && this.currentCompanyCurrencyFormat) {
            return this.currentCompanyCurrencyFormat;
        }
        const currency = this.serverData.get(
            "res.currency",
            "get_company_currency_for_spreadsheet",
            [companyId]
        );
        if (currency.isResolved()) {
            if (!currency.value) {
                return undefined;
            }
            return this.computeFormatFromCurrency(currency.value);
        }
        return currency;
    }
}

featurePluginRegistry.add("odooCurrency", CurrencyPlugin);
