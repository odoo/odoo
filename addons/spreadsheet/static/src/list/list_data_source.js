/** @odoo-module */

import { OdooViewsDataSource } from "@spreadsheet/data_sources/odoo_views_data_source";
import { orderByToString } from "@spreadsheet/helpers/helpers";
import { LoadingDataError } from "@spreadsheet/o_spreadsheet/errors";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import {
    formatDateTime,
    deserializeDateTime,
    formatDate,
    deserializeDate,
} from "@web/core/l10n/dates";

import spreadsheet from "../o_spreadsheet/o_spreadsheet_extended";

const { toNumber } = spreadsheet.helpers;

/**
 * @typedef {import("@spreadsheet/data_sources/metadata_repository").Field} Field
 *
 * @typedef {Object} ListMetaData
 * @property {Array<string>} columns
 * @property {string} resModel
 * @property {Record<string, Field>} fields
 *
 * @typedef {Object} ListSearchParams
 * @property {Array<string>} orderBy
 * @property {Object} domain
 * @property {Object} context
 */

export default class ListDataSource extends OdooViewsDataSource {
    /**
     * @override
     * @param {Object} services Services (see DataSource)
     * @param {Object} params
     * @param {ListMetaData} params.metaData
     * @param {ListSearchParams} params.searchParams
     * @param {number} params.limit
     */
    constructor(services, params) {
        super(services, params);
        this.maxPosition = params.limit;
        this.maxPositionFetched = 0;
        this.data = [];
    }

    /**
     * Increase the max position of the list
     * @param {number} position
     */
    increaseMaxPosition(position) {
        this.maxPosition = Math.max(this.maxPosition, position);
    }

    async _load() {
        await super._load();
        if (this.maxPosition === 0) {
            this.data = [];
            return;
        }
        const { domain, orderBy, context } = this._searchParams;
        this.data = await this._orm.searchRead(
            this._metaData.resModel,
            domain,
            this._getFieldsToFetch(),
            {
                order: orderByToString(orderBy),
                limit: this.maxPosition,
                context,
            }
        );
        this.maxPositionFetched = this.maxPosition;
    }

    /**
     * Get the fields to fetch from the server.
     * Automatically add the currency field if the field is a monetary field.
     */
    _getFieldsToFetch() {
        const fields = this._metaData.columns.filter((f) => this.getField(f));
        for (const field of fields) {
            if (this.getField(field).type === "monetary") {
                fields.push(this.getField(field).currency_field);
            }
        }
        return fields;
    }

    /**
     * @param {number} position
     * @returns {number}
     */
    getIdFromPosition(position) {
        this._assertDataIsLoaded();
        const record = this.data[position];
        return record ? record.id : undefined;
    }

    /**
     * @param {string} fieldName
     * @returns {string}
     */
    getListHeaderValue(fieldName) {
        this._assertDataIsLoaded();
        const field = this.getField(fieldName);
        return field ? field.string : fieldName;
    }

    /**
     * @param {number} position
     * @param {string} fieldName
     * @returns {string|number|undefined}
     */
    getListCellValue(position, fieldName) {
        this._assertDataIsLoaded();
        if (position >= this.maxPositionFetched) {
            this.increaseMaxPosition(position + 1);
            // A reload is needed because the asked position is not already loaded.
            this._triggerFetching();
            throw new LoadingDataError();
        }
        const record = this.data[position];
        if (!record) {
            return "";
        }
        const field = this.getField(fieldName);
        if (!field) {
            throw new Error(
                sprintf(
                    _t("The field %s does not exist or you do not have access to that field"),
                    fieldName
                )
            );
        }
        if (!(fieldName in record)) {
            this._metaData.columns.push(fieldName);
            this._metaData.columns = [...new Set(this._metaData.columns)]; //Remove duplicates
            this._triggerFetching();
            throw new LoadingDataError();
        }
        switch (field.type) {
            case "many2one":
                return record[fieldName].length === 2 ? record[fieldName][1] : "";
            case "one2many":
            case "many2many": {
                const labels = record[fieldName]
                    .map((id) => this._metadataRepository.getRecordDisplayName(field.relation, id))
                    .filter((value) => value !== undefined);
                return labels.join(", ");
            }
            case "selection": {
                const key = record[fieldName];
                const value = field.selection.find((array) => array[0] === key);
                return value ? value[1] : "";
            }
            case "boolean":
                return record[fieldName] ? "TRUE" : "FALSE";
            case "date":
                return record[fieldName] ? toNumber(this._formatDate(record[fieldName])) : "";
            case "datetime":
                return record[fieldName] ? toNumber(this._formatDateTime(record[fieldName])) : "";
            case "properties": {
                const properties = record[fieldName] || [];
                return properties.map((property) => property.string).join(", ");
            }
            case "json":
                throw new Error(sprintf(_t('Fields of type "%s" are not supported'), "json"));
            default:
                return record[fieldName] || "";
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _formatDateTime(dateValue) {
        const date = deserializeDateTime(dateValue);
        return formatDateTime(date, {
            format: "yyyy-MM-dd HH:mm:ss",
            numberingSystem: "latn",
        });
    }

    _formatDate(dateValue) {
        const date = deserializeDate(dateValue);
        return formatDate(date, {
            format: "yyyy-MM-dd",
            numberingSystem: "latn",
        });
    }

    /**
     * Ask the parent data source to force a reload of this data source in the
     * next clock cycle. It's necessary when this.limit was updated and new
     * records have to be fetched.
     */
    _triggerFetching() {
        if (this._fetchingPromise) {
            return;
        }
        this._fetchingPromise = Promise.resolve().then(() => {
            new Promise((resolve) => {
                this.load({ reload: true });
                this._fetchingPromise = undefined;
                resolve();
            });
        });
    }
}
