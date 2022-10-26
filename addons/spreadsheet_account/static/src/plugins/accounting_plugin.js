/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { AccountingDataSource } from "../accounting_datasource";
const DATA_SOURCE_ID = "ACCOUNTING_AGGREGATES";

/**
 * @typedef {import("../accounting_functions").DateRange} DateRange
 */

export default class AccountingPlugin extends spreadsheet.UIPlugin {
    constructor(getters, history, dispatch, config) {
        super(getters, history, dispatch, config);
        this.dataSources = config.dataSources;
        if (this.dataSources) {
            this.dataSources.add(DATA_SOURCE_ID, AccountingDataSource);
        }
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
        return (
            this.dataSources &&
            this.dataSources
                .get(DATA_SOURCE_ID)
                .getCredit(codes, dateRange, offset, companyId, includeUnposted)
        );
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
        return (
            this.dataSources &&
            this.dataSources
                .get(DATA_SOURCE_ID)
                .getDebit(codes, dateRange, offset, companyId, includeUnposted)
        );
    }

    /**
     * @param {Date} date Date included in the fiscal year
     * @param {number | null} companyId specific company to target
     * @returns {string | undefined}
     */
    getFiscalStartDate(date, companyId) {
        return (
            this.dataSources &&
            this.dataSources.get(DATA_SOURCE_ID).getFiscalStartDate(date, companyId)
        );
    }

    /**
     * @param {Date} date Date included in the fiscal year
     * @param {number | undefined} companyId specific company to target
     * @returns {string | undefined}
     */
    getFiscalEndDate(date, companyId) {
        return (
            this.dataSources &&
            this.dataSources.get(DATA_SOURCE_ID).getFiscalEndDate(date, companyId)
        );
    }

    /**
     * @param {string} accountType
     * @returns {string[]}
     */
    getAccountGroupCodes(accountType) {
        return (
            this.dataSources &&
            this.dataSources.get(DATA_SOURCE_ID).getAccountGroupCodes(accountType)
        );
    }
}

AccountingPlugin.getters = [
    "getAccountPrefixCredit",
    "getAccountPrefixDebit",
    "getAccountGroupCodes",
    "getFiscalStartDate",
    "getFiscalEndDate",
];
