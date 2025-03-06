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
        this.pathsToFetch = new Set(["id"]);
        this.alreadyFetchedPaths = new Set();
        this.fieldService = services.env.services.field;
        this.pathToFieldMap = {};
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
     * @param {string} path
     */
    addPathToFetch(path) {
        if (path && !this.alreadyFetchedPaths.has(path)) {
            this.pathsToFetch.add(path);
        }
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
        this.pathToFieldMap = {};
        const { domain, orderBy, context } = this._searchParams;
        const specification = await this._getReadSpec();
        const { records } = await this._orm.webSearchRead(this._metaData.resModel, domain, {
            specification,
            order: orderByToString(orderBy),
            limit: this.maxPosition,
            context,
        });
        this.alreadyFetchedPaths = new Set([...this.pathsToFetch]);
        this.data = records;
        this.maxPositionFetched = this.maxPosition;
    }

    _addSpecForPath(spec, pathInfo) {
        const [first, ...rest] = pathInfo.names;
        const [modelInfo, ...othersModelsInfo] = pathInfo.modelsInfo;
        const field = modelInfo.fieldDefs[first];
        switch (field.type) {
            case "monetary":
                spec[field.name] = {};
                spec[field.currency_field] = {
                    fields: {
                        ...spec[field.currency_field]?.fields,
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
                if (rest.length) {
                    const newPathInfo = { names: rest, modelsInfo: othersModelsInfo };
                    this._addSpecForPath(spec[field.name].fields, newPathInfo);
                }
                break;
            default:
                spec[field.name] = {};
                break;
        }
        return spec;
    }

    /**
     * Get the fields to fetch from the server.
     * Automatically add the currency field if the field is a monetary field.
     */
    async _getReadSpec() {
        const allPaths = await Promise.all(
            [...this.pathsToFetch].map((path) =>
                this.fieldService.loadPath(this._metaData.resModel, path)
            )
        );
        const validPaths = allPaths.filter((result) => !result.isInvalid);
        const spec = {};
        for (const pathInfo of validPaths) {
            this.pathToFieldMap[pathInfo.names.join(".")] =
                pathInfo.modelsInfo.at(-1).fieldDefs[pathInfo.names.at(-1)];
            this._addSpecForPath(spec, pathInfo);
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
     * @param {string} path
     * @returns {string | EvaluationError}
     */
    getListHeaderValue(path) {
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
        const field = this.pathToFieldMap[path];
        return field ? field.string : path;
    }

    /**
     * @returns {object | object[]}
     */
    _getRecordFromRelation(mainRecord, path) {
        const fields = path.split(".");
        let record = mainRecord;
        for (let i = 0; i < fields.length - 1; i++) {
            // Ignore the last one
            if (Array.isArray(record)) {
                record = record.map((r) => r[fields[i]]).flat();
            } else {
                record = record && record[fields[i]];
            }
        }
        return record;
    }

    /**
     * @param {number} position
     * @param {string} path
     * @returns {string|number|undefined|EvaluationError}
     */
    getListCellValue(position, path) {
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
        if (!this.alreadyFetchedPaths.has(path)) {
            this.addPathToFetch(path);
            this._triggerFetching();
            return LOADING_ERROR;
        }
        const field = this.getFieldFromPath(path);
        if (!field) {
            return new EvaluationError(
                _t("The field %s does not exist or you do not have access to that field", path)
            );
        }
        const mainRecord = this.data[position];
        if (!mainRecord) {
            return "";
        }
        this.assertIsValid();
        const record = this._getRecordFromRelation(mainRecord, path);
        if (!record) {
            return "";
        }
        const lastField = path.split(".").at(-1);
        if (Array.isArray(record)) {
            // remove duplicates?
            // needs to be formatted...
            return record.map((r) => this._parseServerValue(field, r[lastField])).join(", ");
        }
        return this._parseServerValue(field, record[lastField]);
    }

    _parseServerValue(field, value) {
        switch (field.type) {
            case "many2one":
                return value.display_name ?? "";
            case "one2many":
            case "many2many": {
                const labels = value
                    .map(({ display_name }) => display_name)
                    .filter((displayName) => displayName !== undefined);
                return labels.join(", ");
            }
            case "selection": {
                const key = value;
                const selectedOption = field.selection.find((array) => array[0] === key);
                return selectedOption ? selectedOption[1] : "";
            }
            case "boolean":
                return value ? true : false;
            case "date":
                return value ? toNumber(this._formatDate(value), DEFAULT_LOCALE) : "";
            case "datetime":
                return value ? toNumber(this._formatDateTime(value), DEFAULT_LOCALE) : "";
            case "properties": {
                const properties = value || [];
                return properties.map((property) => property.string).join(", ");
            }
            case "json":
                return new EvaluationError(_t('Fields of type "%s" are not supported', "json"));
            default:
                return value || "";
        }
    }

    /**
     * @param {number} position
     * @param {string} path
     * @param {string} currencyFieldName
     * @returns {import("@spreadsheet/currency/currency_data_source").Currency | undefined}
     */
    getListCurrency(position, path, currencyFieldName) {
        this.assertIsValid();
        const currency = this._getRecordFromRelation(this.data[position], path)?.[
            currencyFieldName
        ];
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

    getFieldFromPath(path) {
        return this.pathToFieldMap[path];
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
        this._fetchingPromise = Promise.resolve().then(
            () =>
                new Promise((resolve) => {
                    this._fetchingPromise = undefined;
                    this.load({ reload: true });
                    resolve();
                })
        );
    }
}
