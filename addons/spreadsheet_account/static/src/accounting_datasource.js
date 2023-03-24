/** @odoo-module */
import { camelToSnakeObject, toServerDateString } from "@spreadsheet/helpers/helpers";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

import { ServerData } from "@spreadsheet/data_sources/server_data";

/**
 * @typedef {import("./accounting_functions").DateRange} DateRange
 */

export class AccountingDataSource {
    constructor(services) {
        this.serverData = new ServerData(services.orm, {
            whenDataIsFetched: () => services.notify(),
        });
    }

    /**
     * Gets the total credit for a given account code prefix
     * @param {string[]} codes prefixes of the accounts codes
     * @param {DateRange} dateRange start date of the period to look
     * @param {number} offset end date of the period to look
     * @param {number} companyId specific company to target
     * @param {boolean} includeUnposted wether or not select unposted entries
     * @returns {number | undefined}
     */
    getCredit(codes, dateRange, offset, companyId, includeUnposted) {
        const data = this._fetchAccountData(codes, dateRange, offset, companyId, includeUnposted);
        return data.credit;
    }

    /**
     * Gets the total debit for a given account code prefix
     * @param {string[]} codes prefixes of the accounts codes
     * @param {DateRange} dateRange start date of the period to look
     * @param {number} offset end  date of the period to look
     * @param {number} companyId specific company to target
     * @param {boolean} includeUnposted wether or not select unposted entries
     * @returns {number | undefined}
     */
    getDebit(codes, dateRange, offset, companyId, includeUnposted) {
        const data = this._fetchAccountData(codes, dateRange, offset, companyId, includeUnposted);
        return data.debit;
    }

    /**
     * @param {Date} date
     * @param {number | null} companyId
     * @returns {string}
     */
    getFiscalStartDate(date, companyId) {
        return this._fetchCompanyData(date, companyId).start;
    }

    /**
     * @param {Date} date
     * @param {number | null} companyId
     * @returns {string}
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
     * @param {DateRange} dateRange start date of the period to look
     * @param {number} offset end  date of the period to look
     * @param {number | null} companyId specific companyId to target
     * @param {boolean} includeUnposted wether or not select unposted entries
     * @returns {{ debit: number, credit: number }}
     */
    _fetchAccountData(codes, dateRange, offset, companyId, includeUnposted) {
        dateRange.year += offset;
        // Excel dates start at 1899-12-30, we should not support date ranges
        // that do not cover dates prior to it.
        // Unfortunately, this check needs to be done right before the server
        // call as a date to low (year <= 1) can raise an error server side.
        if (dateRange.year < 1900) {
            throw new Error(sprintf(_t("%s is not a valid year."), dateRange.year));
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
     * @returns {{start: string, end: string}}
     */
    _fetchCompanyData(date, companyId) {
        const result = this.serverData.batch.get("res.company", "get_fiscal_dates", {
            date: toServerDateString(date),
            company_id: companyId,
        });
        if (result === false) {
            throw new Error(_t("The company fiscal year could not be found."));
        }
        return result;
    }
}
