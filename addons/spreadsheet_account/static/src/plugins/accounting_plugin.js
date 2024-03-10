/** @odoo-module */
// @ts-check

import { EvaluationError } from "@odoo/o-spreadsheet";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { _t } from "@web/core/l10n/translation";
import { camelToSnakeObject, toServerDateString } from "@spreadsheet/helpers/helpers";

/**
 * @typedef {import("../accounting_functions").DateRange} DateRange
 *
 * @typedef {import("@odoo/o-spreadsheet").FPayload} FPayload
 */

export class AccountingPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ ([
        "getAccountPrefixCredit",
        "getAccountPrefixDebit",
        "getAccountGroupCodes",
        "getFiscalStartDate",
        "getFiscalEndDate",
    ]);
    constructor(config) {
        super(config);
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
     * Gets the total balance for given account code prefix
     * @param {string[]} codes prefixes of the accounts' codes
     * @param {DateRange} dateRange start date of the period to look
     * @param {number} offset end  date of the period to look
     * @param {number | null} companyId specific company to target
     * @param {boolean} includeUnposted wether or not select unposted entries
     * @returns {FPayload}
     */
    getAccountPrefixCredit(codes, dateRange, offset, companyId, includeUnposted) {
        const format = this.getters.getCompanyCurrencyFormat(companyId);
        return this._fetchAccountData(
            codes,
            dateRange,
            offset,
            companyId,
            includeUnposted
        ).toEvaluationValueWithFormat(format, "credit");
    }

    /**
     * Gets the total balance for a given account code prefix
     * @param {string[]} codes prefixes of the accounts codes
     * @param {DateRange} dateRange start date of the period to look
     * @param {number} offset end  date of the period to look
     * @param {number | null} companyId specific company to target
     * @param {boolean} includeUnposted wether or not select unposted entries
     * @returns {FPayload}
     */
    getAccountPrefixDebit(codes, dateRange, offset, companyId, includeUnposted) {
        const format = this.getters.getCompanyCurrencyFormat(companyId);
        return this._fetchAccountData(
            codes,
            dateRange,
            offset,
            companyId,
            includeUnposted
        ).toEvaluationValueWithFormat(format, "debit");
    }

    /**
     * @param {Date} date Date included in the fiscal year
     * @param {number | null} companyId specific company to target
     * @returns {FPayload}
     */
    getFiscalStartDate(date, companyId) {
        return this._fetchCompanyData(date, companyId).toEvaluationValue("start");
    }

    /**
     * @param {Date} date Date included in the fiscal year
     * @param {number | undefined} companyId specific company to target
     * @returns {FPayload}
     */
    getFiscalEndDate(date, companyId) {
        return this._fetchCompanyData(date, companyId).toEvaluationValue("end");
    }

    /**
     * @param {string} accountType
     * @returns {FPayload}
     */
    getAccountGroupCodes(accountType) {
        const codes = this.serverData.batch.get(
            "account.account",
            "get_account_group",
            accountType
        );
        if (codes.isResolved()) {
            return { value: codes.value.join(",") };
        }
        return codes.toEvaluationValue();
    }

    /**
     * Fetch the account information (credit/debit) for a given account code
     * @private
     * @param {string[]} codes prefix of the accounts' codes
     * @param {DateRange} dateRange start date of the period to look
     * @param {number} offset end  date of the period to look
     * @param {number | null} companyId specific companyId to target
     * @param {boolean} includeUnposted wether or not select unposted entries
     * @returns {import("@spreadsheet/data_sources/loadable").Loadable}
     */
    _fetchAccountData(codes, dateRange, offset, companyId, includeUnposted) {
        dateRange.year += offset;
        // TODO move this ?
        // Excel dates start at 1899-12-30, we should not support date ranges
        // that do not cover dates prior to it.
        // Unfortunately, this check needs to be done right before the server
        // call as a date to low (year <= 1) can raise an error server side.
        if (dateRange.year < 1900) {
            throw new EvaluationError(_t("%s is not a valid year.", dateRange.year));
        }
        return this.serverData.batch.get(
            "account.account",
            "spreadsheet_fetch_debit_credit",
            camelToSnakeObject({ dateRange, codes, companyId, includeUnposted })
        );
    }

    /**
     * Fetch the start and end date of the fiscal year enclosing a given date
     * Defaults on the current user company if not provided
     * @private
     * @param {Date} date
     * @param {number | null} companyId
     * @returns {import("@spreadsheet/data_sources/loadable").Loadable}
     */
    _fetchCompanyData(date, companyId) {
        return this.serverData.batch.get("res.company", "get_fiscal_dates", {
            date: toServerDateString(date),
            company_id: companyId,
        });
    }
}
