// @ts-check
import { OdooEvaluationPlugin } from "@spreadsheet/plugins";
import { deepCopy } from "@web/core/utils/objects";
import { camelToSnakeObject, toServerDateString } from "@spreadsheet/helpers/helpers";

/**
 * @typedef {import("../accounting_functions").DateRange} DateRange
 */

export class AccountingPlugin extends OdooEvaluationPlugin {
    static getters = /** @type {const} */ ([
        "getAccountPrefixCredit",
        "getAccountPrefixDebit",
        "getAccountGroupCodes",
        "getFiscalDates",
        "getAccountResidual",
        "getAccountPartnerData",
        "getAccountTagData",
        "getCurrentFiscalYearStart",
        "getCurrentFiscalYearEnd",
    ]);
    constructor(config) {
        super(config);
        this.currentFiscalYearStart = config.custom.currentFiscalYearStart;
        this.currentFiscalYearEnd = config.custom.currentFiscalYearEnd;
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
     * @returns {number}
     */
    getAccountPrefixCredit(codes, dateRange, offset, companyId, includeUnposted) {
        const data = this._fetchAccountData(codes, dateRange, offset, companyId, includeUnposted);
        return data.credit;
    }

    /**
     * Gets the total balance for a given account code prefix
     * @param {string[]} codes prefixes of the accounts codes
     * @param {DateRange} dateRange start date of the period to look
     * @param {number} offset end  date of the period to look
     * @param {number | null} companyId specific company to target
     * @param {boolean} includeUnposted wether or not select unposted entries
     * @returns {number}
     */
    getAccountPrefixDebit(codes, dateRange, offset, companyId, includeUnposted) {
        const data = this._fetchAccountData(codes, dateRange, offset, companyId, includeUnposted);
        return data.debit;
    }

    /**
     * Gets the start and end date of the fiscal year enclosing a given date
     * Defaults on the current user company if not provided
     * @param {Date} date
     * @param {number | null} companyId specific company to target
     * @returns {{start: string, end: string} | false}
     */
    getFiscalDates(date, companyId) {
        return this.serverData.batch.get("res.company", "get_fiscal_dates", {
            date: toServerDateString(date),
            company_id: companyId,
        });
    }

    getCurrentFiscalYearStart() {
        return this.currentFiscalYearStart;
    }

    getCurrentFiscalYearEnd() {
        return this.currentFiscalYearEnd;
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
     * @param {DateRange} dateRange start date of the period to look
     * @param {number} offset end  date of the period to look
     * @param {number | null} companyId specific companyId to target
     * @param {boolean} includeUnposted wether or not select unposted entries
     * @returns {{ debit: number, credit: number }}
     */
    _fetchAccountData(codes, dateRange, offset, companyId, includeUnposted) {
        dateRange = deepCopy(dateRange);
        dateRange.year += offset;
        return this.serverData.batch.get(
            "account.account",
            "spreadsheet_fetch_debit_credit",
            camelToSnakeObject({ dateRange, codes, companyId, includeUnposted })
        );
    }

    /**
     * Gets the residual amount for given account code prefixes over a given period
     * @param {string[]} codes prefixes of the accounts codes
     * @param {DateRange} dateRange start date of the period to look
     * @param {number} offset year offset of the period to search
     * @param {number} companyId specific company to target
     * @param {boolean} includeUnposted whether or not select unposted entries
     * @returns {number | undefined}
     */
    getAccountResidual(codes, dateRange, offset, companyId, includeUnposted) {
        dateRange = deepCopy(dateRange);
        dateRange.year += offset;
        return this.serverData.batch.get(
            "account.account",
            "spreadsheet_fetch_residual_amount",
            camelToSnakeObject({ codes, dateRange, companyId, includeUnposted })
        );
    }

    /**
     * Fetch the account information for a given account code and partner
     * @private
     * @param {string[]} codes prefix of the accounts' codes
     * @param {DateRange} dateRange start date of the period to look
     * @param {number} offset year offset of the period to look
     * @param {number | null} companyId specific companyId to target
     * @param {boolean} includeUnposted wether or not select unposted entries
     * @param {number[]} partnerIds ids of the partners
     * @returns {number | undefined}
     */
    getAccountPartnerData(codes, dateRange, offset, companyId, includeUnposted, partnerIds) {
        dateRange = deepCopy(dateRange);
        dateRange.year += offset;
        return this.serverData.batch.get(
            "account.account",
            "spreadsheet_fetch_partner_balance",
            camelToSnakeObject({ dateRange, codes, companyId, includeUnposted, partnerIds })
        );
    }

    /**
     * Fetch the balance for a given account tag
     * @private
     * @param {number[]} accountTagIds ids of the account tags
     * @param {DateRange} dateRange start date of the period to look
     * @param {number} offset year offset of the period to look
     * @param {number | null} companyId specific companyId to target
     * @param {boolean} includeUnposted wether or not select unposted entries
     * @returns {number | undefined}
     */
    getAccountTagData(accountTagIds, dateRange, offset, companyId, includeUnposted) {
        dateRange = deepCopy(dateRange);
        dateRange.year += offset;
        return this.serverData.batch.get(
            "account.account",
            "spreadsheet_fetch_balance_tag",
            camelToSnakeObject({ accountTagIds, dateRange, companyId, includeUnposted })
        );
    }
}
