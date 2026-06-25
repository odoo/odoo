import { EvaluationError, registries } from "@odoo/o-spreadsheet";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { toServerDateString } from "@spreadsheet/helpers/helpers";
import { _t } from "@web/core/l10n/translation";
import { computeFormatFromCurrency } from "../helpers";
const { featurePluginRegistry } = registries;

export class CurrencyPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ (["getCurrencyRate", "getCompanyCurrencyFormat"]);

    constructor(config) {
        super(config);
        /** @type {string | undefined} */
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
        if (rate === false) {
            throw new EvaluationError(_t("Currency rate unavailable."));
        }
        return rate;
    }

    /**
     * Returns the default display format of a the company currency
     * @param {number} [companyId]
     * @returns {string | undefined}
     */
    getCompanyCurrencyFormat(companyId) {
        if (!companyId && this.currentCompanyCurrency) {
            return computeFormatFromCurrency(this.currentCompanyCurrency);
        }
        const currency = this.serverData.get(
            "res.currency",
            "get_company_currency_for_spreadsheet",
            [companyId]
        );
        if (currency === false) {
            throw new EvaluationError(_t("Currency not available for this company."));
        }
        return computeFormatFromCurrency(currency);
    }
}

featurePluginRegistry.add("odooCurrency", CurrencyPlugin);
