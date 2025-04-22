/** @odoo-module */

import { OdooViewsDataSource } from "@spreadsheet/data_sources/odoo_views_data_source";
import { EvaluationError } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import {
    formatDateTime,
    deserializeDateTime,
    formatDate,
    deserializeDate,
} from "@web/core/l10n/dates";
import { orderByToString } from "@web/search/utils/order_by";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { LOADING_ERROR } from "@spreadsheet/data_sources/data_source";

const { toNumber } = spreadsheet.helpers;
const { DEFAULT_LOCALE } = spreadsheet.constants;

/**
 * @typedef {import("@spreadsheet").OdooFields} OdooFields
 *
 * @typedef {Object} ListMetaData
 * @property {Array<string>} columns
 * @property {string} resModel
 * @property {OdooFields} fields
 *
 * @typedef {Object} ListSearchParams
 * @property {Array<string>} orderBy
 * @property {Object} domain
 * @property {Object} context
 */

export class ListDataSource extends OdooViewsDataSource {
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
        this.maxPosition = 0;
        this.maxPositionFetched = 0;
        this.data = [];
        this.fieldsToFetch = new Set();
    }

    /**
     * Increase the max position of the list
     * @param {number} position
     */
    increaseMaxPosition(position) {
        this.maxPosition = Math.max(this.maxPosition, position);
    }

    isModelValid() {
        return this._isModelValid;
    }

    /**
     * @param {string} fieldName
     */
    addFieldToFetch(fieldName) {
        if (this.data.length && fieldName in this.data[0]) {
            return;
        }
        this.fieldsToFetch.add(fieldName);
    }

    async load(params) {
        if (this._fetchingPromise) {
            // if fetching is already scheduled for the next tick,
            // wait the fetching promise to trigger the data source loading
            // and then await the loading.
            await this._fetchingPromise;
            await this._loadPromise;
            return;
        }
        return super.load(params);
    }

    async _load() {
        await super._load();
        if (this.maxPosition === 0) {
            this.data = [];
            return;
        }
        const { domain, orderBy, context } = this._searchParams;
        const { records } = await this._orm.webSearchRead(this._metaData.resModel, domain, {
            specification: this._getReadSpec(),
            order: orderByToString(orderBy),
            limit: this.maxPosition,
            context,
        });
        this.data = records;
        this.maxPositionFetched = this.maxPosition;
    }

    /**
     * Get the fields to fetch from the server.
     * Automatically add the currency field if the field is a monetary field.
     */
    _getReadSpec() {
        const spec = {};
        const fields = [...this.fieldsToFetch].map((f) => this.getField(f)).filter(Boolean);
        for (const field of fields) {
            switch (field.type) {
                case "monetary":
                    spec[field.name] = {};
                    spec[field.currency_field] = {
                        fields: {
                            ...spec[field.currency_field]?.fields,
                            display_name: {},
                            name: {}, // currency code
                            symbol: {},
                            decimal_places: {},
                            position: {},
                        },
                    };
                    break;
                case "many2one":
                case "many2many":
                case "one2many":
                    spec[field.name] = {
                        fields: {
                            display_name: {},
                            ...spec[field.name]?.fields,
                        },
                    };
                    break;
                default:
                    spec[field.name] = {};
                    break;
            }
        }
        return spec;
    }

    /**
     * @param {number} position
     * @returns {number}
     */
    getIdFromPosition(position) {
        this.assertIsValid();
        const record = this.data[position];
        return record ? record.id : undefined;
    }

    /**
     * @param {string} fieldName
     * @returns {string | EvaluationError}
     */
    getListHeaderValue(fieldName) {
        if (this.isLoading()) {
            return LOADING_ERROR;
        }
        if (!this._isValid || !this._isModelValid) {
            return this._loadError;
        }
        if (!this.isMetaDataLoaded()) {
            this._triggerFetching();
            return LOADING_ERROR;
        }
        this.assertIsValid();
        const field = this.getField(fieldName);
        return field ? field.string : fieldName;
    }

    /**
     * @param {number} position
     * @param {string} fieldName
     * @returns {string|number|undefined|EvaluationError}
     */
    getListCellValue(position, fieldName) {
        if (this.isLoading()) {
            return LOADING_ERROR;
        }
        if (!this._isValid || !this._isModelValid) {
            return this._loadError;
        }
        if (position >= this.maxPositionFetched) {
            this.increaseMaxPosition(position + 1);
            // A reload is needed because the asked position is not already loaded.
            this._triggerFetching();
            return LOADING_ERROR;
        }
        const record = this.data[position];
        if (!record) {
            return "";
        }
        const field = this.getField(fieldName);
        if (!field) {
            return new EvaluationError(
                _t("The field %s does not exist or you do not have access to that field", fieldName)
            );
        }
        if (!(fieldName in record)) {
            this.addFieldToFetch(fieldName);
            this._triggerFetching();
            return LOADING_ERROR;
        }
        this.assertIsValid();
        switch (field.type) {
            case "many2one":
                return record[fieldName].display_name ?? "";
            case "one2many":
            case "many2many": {
                const labels = record[fieldName]
                    .map(({ display_name }) => display_name)
                    .filter((displayName) => displayName !== undefined);
                return labels.join(", ");
            }
            case "selection": {
                const key = record[fieldName];
                const value = field.selection.find((array) => array[0] === key);
                return value ? value[1] : "";
            }
            case "boolean":
                return record[fieldName] ? true : false;
            case "date":
                return record[fieldName]
                    ? toNumber(this._formatDate(record[fieldName]), DEFAULT_LOCALE)
                    : "";
            case "datetime":
                return record[fieldName]
                    ? toNumber(this._formatDateTime(record[fieldName]), DEFAULT_LOCALE)
                    : "";
            case "properties": {
                const properties = record[fieldName] || [];
                return properties.map((property) => property.string).join(", ");
            }
            case "json":
                return new EvaluationError(_t('Fields of type "%s" are not supported', "json"));
            default:
                return record[fieldName] || "";
        }
    }

    /**
     * @param {number} position
     * @param {string} currencyFieldName
     * @returns {import("@spreadsheet/currency/currency_data_source").Currency | undefined}
     */
    getListCurrency(position, currencyFieldName) {
        this.assertIsValid();
        const currency = this.data[position]?.[currencyFieldName];
        if (!currency) {
            return undefined;
        }
        return {
            code: currency.name,
            symbol: currency.symbol,
            decimalPlaces: currency.decimal_places,
            position: currency.position,
        };
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _formatDateTime(dateValue) {
        const date = deserializeDateTime(dateValue);
        return formatDateTime(date.reconfigure({ numberingSystem: "latn" }), {
            format: "yyyy-MM-dd HH:mm:ss",
        });
    }

    _formatDate(dateValue) {
        const date = deserializeDate(dateValue);
        return formatDate(date.reconfigure({ numberingSystem: "latn" }), {
            format: "yyyy-MM-dd",
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
            return new Promise((resolve) => {
                this._fetchingPromise = undefined;
                this.load({ reload: true });
                resolve();
            });
        });
    }
}
