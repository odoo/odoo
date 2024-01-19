// @ts-check

import { EvaluationError } from "@odoo/o-spreadsheet";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { _t } from "@web/core/l10n/translation";
import { deepCopy } from "@web/core/utils/objects";
import { camelToSnakeObject, toServerDateString } from "@spreadsheet/helpers/helpers";

/**
 * @typedef {import("../accounting_functions").DateRange} DateRange
 */

export class AccountingPlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ ([
        "getAccountPrefixCredit",
        "getAccountPrefixDebit",
        "getAccountGroupCodes",
        "getFiscalStartDate",
        "getFiscalEndDate",
        "getAccountResidual",
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
     * @param {DateRange} dateFrom start date of the period to look
     * @param {DateRange} dateTo end date of the period to look
     * @param {number} offset year offset of the period to look
     * @param {number | null} companyId specific company to target
     * @param {boolean} includeUnposted wether or not select unposted entries
     * @returns {number}
     */
    getAccountPrefixCredit(codes, dateFrom, dateTo, offset, companyId, includeUnposted) {
        const data = this._fetchAccountData(codes, dateFrom, dateTo, offset, companyId, includeUnposted);
        return data.credit;
    }

    /**
     * Gets the total balance for a given account code prefix
     * @param {string[]} codes prefixes of the accounts' codes
     * @param {DateRange} dateFrom start date of the period to look
     * @param {DateRange} dateTo end date of the period to look
     * @param {number} offset year offset of the period to look
     * @param {number | null} companyId specific company to target
     * @param {boolean} includeUnposted wether or not select unposted entries
     * @returns {number}
     */
    getAccountPrefixDebit(codes, dateFrom, dateTo, offset, companyId, includeUnposted) {
        const data = this._fetchAccountData(codes, dateFrom, dateTo, offset, companyId, includeUnposted);
        return data.debit;
    }

    /**
     * @param {Date} date Date included in the fiscal year
     * @param {number | undefined} companyId specific company to target
     * @returns {string | undefined}
     */
    getFiscalStartDate(date, companyId) {
        return this._fetchCompanyData(date, companyId).start;
    }

    /**
     * @param {Date} date Date included in the fiscal year
     * @param {number | undefined} companyId specific company to target
     * @returns {string | undefined}
     */
    getFiscalEndDate(date, companyId) {
        return this._fetchCompanyData(date, companyId).end;
    }

    /**
     * @param {string} accountType
     * @returns {string[]}
     */
    getAccountGroupCodes(accountType) {
        return this.serverData.batch.get("account.account", "get_account_group", accountType);
    }

    /**
     * Fetch the account information (credit/debit) for a given account code
     * @private
     * @param {string[]} codes prefix of the accounts' codes
     * @param {DateRange} dateFrom start date of the period to look
     * @param {DateRange} dateTo end date of the period to look
     * @param {number} offset year offset of the period to look
     * @param {number | null} companyId specific companyId to target
     * @param {boolean} includeUnposted wether or not select unposted entries
     * @returns {{ debit: number, credit: number }}
     */
    _fetchAccountData(codes, dateFrom, dateTo, offset, companyId, includeUnposted) {
        dateFrom = deepCopy(dateFrom);
        dateTo = deepCopy(dateTo);
        dateFrom.year += offset;
        dateTo.year += offset;
        // Excel dates start at 1899-12-31 and end at 9999-12-31 (inclusive), we
        // should not support date ranges outside of it.
        if ( dateFrom.year < 1900 || dateFrom.year > 9999 ) {
            throw new EvaluationError(_t("%s is not a valid year.", dateFrom.year));
        }
        if ( dateTo.year < 1900 || dateTo.year > 9999 ) {
            throw new EvaluationError(_t("%s is not a valid year.", dateTo.year));
        }
        return this.serverData.batch.get(
            "account.account",
            "spreadsheet_fetch_debit_credit",
            camelToSnakeObject({ dateFrom, dateTo, codes, companyId, includeUnposted })
        );
    }

    /**
     * Fetch the start and end date of the fiscal year enclosing a given date
     * Defaults on the current user company if not provided
     * @private
     * @param {Date} date
     * @param {number | undefined} companyId
     * @returns {{start: string, end: string}}
     */
    _fetchCompanyData(date, companyId) {
        const result = this.serverData.batch.get("res.company", "get_fiscal_dates", {
            date: toServerDateString(date),
            company_id: companyId,
        });
        if (result === false) {
            throw new EvaluationError(_t("The company fiscal year could not be found."));
        }
        return result;
    }

    /**
     * Gets the residual amount for given account code prefixes over a given period
     * @param {string[]} codes prefixes of the accounts codes
     * @param {DateRange} dateFrom start date of the period to search
     * @param {DateRange} dateTo end date of the period to search
     * @param {number} offset year offset of the period to search
     * @param {number} companyId specific company to target
     * @param {boolean} includeUnposted whether or not select unposted entries
     * @returns {number | undefined}
     */
    getAccountResidual(codes, dateFrom, dateTo, offset, companyId, includeUnposted) {
        dateFrom = deepCopy(dateFrom);
        dateTo = deepCopy(dateTo);
        dateFrom.year += offset;
        dateTo.year += offset;
        // Excel dates start at 1899-12-31 and end at 9999-12-31 (inclusive), we
        // should not support date ranges outside of it.
        if ( dateFrom.year < 1900 || dateFrom.year > 9999 ) {
            throw new EvaluationError(_t("%s is not a valid year.", dateFrom.year));
        }
        if ( dateTo.year < 1900 || dateTo.year > 9999 ) {
            throw new EvaluationError(_t("%s is not a valid year.", dateTo.year));
        }
        const result = this.serverData.batch.get(
            "account.account",
            "spreadsheet_fetch_residual_amount",
            camelToSnakeObject({ codes, dateFrom, dateTo, companyId, includeUnposted })
        );
        if (result === false) {
            throw new EvaluationError(_t("The residual amount for given accounts could not be computed."));
        }
        return result.amount_residual;
    }
}
