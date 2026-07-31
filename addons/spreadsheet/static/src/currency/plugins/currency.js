import { registries } from "@odoo/o-spreadsheet";
import { OdooEvaluationPlugin } from "@spreadsheet/plugins";
import { toServerDateString } from "@spreadsheet/helpers/helpers";
import { computeFormatFromCurrency } from "../helpers";
const { evaluationPluginRegistry } = registries;

export class CurrencyPlugin extends OdooEvaluationPlugin {
    static getters = /** @type {const} */ ([
        "getCurrencyRate",
        "getCompanyCurrency",
        "getCompanyCurrencyFormat",
    ]);

    constructor(config) {
        super(config);
        /** @type {import("../helpers").Currency | undefined} */
        this.currentCompanyCurrency = config.defaultCurrency;
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
     * @param {string | undefined} date
     * @param {number | undefined} companyId
     * @returns {number|string}
     */
    getCurrencyRate(from, to, date, companyId) {
        const data = this.serverData.batch.get("res.currency.rate", "get_rates_for_spreadsheet", {
            from,
            to,
            date: date ? toServerDateString(date) : undefined,
            company_id: companyId,
        });
        const rate = data !== undefined ? data.rate : undefined;
        return rate;
    }

    /**
     * Get the currency of the given company, or the current company's
     * currency if no company id is provided.
     * @param {number | undefined} [companyId]
     * @returns {import("../helpers").Currency | false}
     */
    getCompanyCurrency(companyId) {
        if (!companyId && this.currentCompanyCurrency) {
            return this.currentCompanyCurrency;
        }
        return this.serverData.get("res.currency", "get_company_currency_for_spreadsheet", [
            companyId,
        ]);
    }

    /**
     * Returns the default display format of a the company currency
     * @param {number} [companyId]
     * @returns {string | undefined}
     */
    getCompanyCurrencyFormat(companyId) {
        return computeFormatFromCurrency(this.getCompanyCurrency(companyId));
    }
}

evaluationPluginRegistry.add("odooCurrency", CurrencyPlugin);
