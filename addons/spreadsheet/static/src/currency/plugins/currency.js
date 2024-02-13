/** @odoo-module */

import { helpers, registries } from "@odoo/o-spreadsheet";
import { CurrencyDataSource } from "../currency_data_source";
import { OdooUIPlugin } from "@spreadsheet/plugins";
const { featurePluginRegistry } = registries;
const { createCurrencyFormat } = helpers;

const DATA_SOURCE_ID = "CURRENCIES";

/**
 * @typedef {import("../currency_data_source").Currency} Currency
 */

export class CurrencyPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ ([
        "getCurrencyRate",
        "computeFormatFromCurrency",
        "getCompanyCurrencyFormat",
    ]);

    constructor(config) {
        super(config);
        this.dataSources = config.custom.dataSources;
        if (this.dataSources) {
            this.dataSources.add(DATA_SOURCE_ID, CurrencyDataSource);
        }
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    /**
     * Get the currency rate between the two given currencies
     * @param {string} from Currency from
     * @param {string} to Currency to
     * @param {string} date
     * @returns {number|string}
     */
    getCurrencyRate(from, to, date) {
        return (
            this.dataSources && this.dataSources.get(DATA_SOURCE_ID).getCurrencyRate(from, to, date)
        );
    }

    /**
     * @param {Currency | undefined} currency     *
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
     * @returns {string | undefined}
     */
    getCompanyCurrencyFormat(companyId) {
        const currency =
            this.dataSources &&
            this.dataSources.get(DATA_SOURCE_ID).getCompanyCurrencyFormat(companyId);
        return this.computeFormatFromCurrency(currency);
    }
}

featurePluginRegistry.add("odooCurrency", CurrencyPlugin);
