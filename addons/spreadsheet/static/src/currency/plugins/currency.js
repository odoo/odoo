/** @odoo-module */

import spreadsheet from "../../o_spreadsheet/o_spreadsheet_extended";
import { CurrencyDataSource } from "../currency_data_source";
const { featurePluginRegistry } = spreadsheet.registries;

const DATA_SOURCE_ID = "CURRENCIES";

/**
 * @typedef {import("../currency_data_source").Currency} Currency
 */

class CurrencyPlugin extends spreadsheet.UIPlugin {
    constructor(config) {
        super(config);
        this.dataSources = config.external.dataSources;
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
     *
     * @param {Currency | undefined} currency
     * @private
     *
     * @returns {string | undefined}
     */
    computeFormatFromCurrency(currency) {
        if (!currency) {
            return undefined;
        }
        const decimalFormatPart = currency.decimalPlaces
            ? "." + "0".repeat(currency.decimalPlaces)
            : "";
        const numberFormat = "#,##0" + decimalFormatPart;
        const symbolFormatPart = "[$" + currency.symbol + "]";
        return currency.position === "after"
            ? numberFormat + symbolFormatPart
            : symbolFormatPart + numberFormat;
    }

    /**
     * Returns the default display format of a given currency
     * @param {string} currencyName
     * @returns {string | undefined}
     */
    getCurrencyFormat(currencyName) {
        const currency =
            currencyName &&
            this.dataSources &&
            this.dataSources.get(DATA_SOURCE_ID).getCurrency(currencyName);
        return this.computeFormatFromCurrency(currency);
    }

    /**
     * Returns the default display format of a the company currency
     * @param {number|undefined} companyId
     * @returns {string | undefined}
     */
    getCompanyCurrencyFormat(companyId) {
        const currency =
            this.dataSources &&
            this.dataSources.get(DATA_SOURCE_ID).getCompanyCurrencyFormat(companyId);
        return this.computeFormatFromCurrency(currency);
    }
}

CurrencyPlugin.getters = ["getCurrencyRate", "getCurrencyFormat", "getCompanyCurrencyFormat"];

featurePluginRegistry.add("odooCurrency", CurrencyPlugin);
