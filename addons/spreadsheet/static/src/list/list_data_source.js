/** @odoo-module native */
import { EvaluationError } from "@odoo/o-spreadsheet";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { LOADING_ERROR } from "@spreadsheet/data_sources/data_source";
import { OdooViewsDataSource } from "@spreadsheet/data_sources/odoo_views_data_source";
import { makeLogger } from "@web/core/debug/debug_logger";
import {
    deserializeDate,
    deserializeDateTime,
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";
import { _t } from "@web/core/translation";
import { orderByToString } from "@web/core/utils/order_by";

const { toNumber } = spreadsheet.helpers;

const log = makeLogger("spreadsheet.list");
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
        this.fieldPathsToFetch = new Set(["id"]);
        this.alreadyFetchedFieldPaths = new Set();
        this.fieldService = services.env.services.field;
        this.fieldPathsToFieldMap = {};
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
     * @param {string} fieldPath
     */
    addFieldPathToFetch(fieldPath) {
        if (fieldPath && !this.alreadyFetchedFieldPaths.has(fieldPath)) {
            this.fieldPathsToFetch.add(fieldPath);
        }
    }

    async load(params) {
        if (this._fetchingPromise) {
            log.logic("load:joinScheduledFetch", () => ({
                model: this._metaData.resModel,
            }));
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
            log.logic("load:skipped", () => ({
                model: this._metaData.resModel,
                reason: "maxPosition=0",
            }));
            this.data = [];
            return;
        }
        this.fieldPathsToFieldMap = {};
        const { domain, orderBy, context } = this._searchParams;
        const specification = await this._getReadSpec();
        log.pipeline("load", () => ({
            model: this._metaData.resModel,
            limit: this.maxPosition,
            fieldPaths: [...this.fieldPathsToFetch],
            domain,
        }));
        const endRead = log.perf("webSearchRead");
        const { records } = await this._orm.webSearchRead(
            this._metaData.resModel,
            domain,
            {
                specification,
                order: orderByToString(orderBy),
                limit: this.maxPosition,
                context,
            },
        );
        endRead({ model: this._metaData.resModel, records: records.length });
        this.alreadyFetchedFieldPaths = new Set([...this.fieldPathsToFetch]);
        this.data = records;
        this.maxPositionFetched = this.maxPosition;
    }

    /**
     * The currency of a monetary value is a separate record: ask for the parts
     * the spreadsheet needs to format with.
     */
    _addCurrencySpec(spec, currencyField) {
        spec[currencyField] = {
            fields: {
                ...spec[currencyField]?.fields,
                name: {}, // currency code
                symbol: {},
                decimal_places: {},
                position: {},
            },
        };
    }

    /**
     * Automatically add the currency field if the field is a monetary field.
     */
    _addSpecForFieldPath(spec, pathInfo) {
        const [first, ...rest] = pathInfo.names;
        const [modelInfo, ...othersModelsInfo] = pathInfo.modelsInfo;
        const field = modelInfo.fieldDefs[first];
        switch (field.type) {
            case "monetary":
                spec[field.name] = {};
                this._addCurrencySpec(spec, field.currency_field);
                break;
            case "properties": {
                // The whole blob comes back in one read, so the properties
                // field itself is all we ask for. `rest` holds the property
                // names the columns picked out of it, and a monetary one still
                // needs its currency, which lives on this record.
                spec[field.name] = {};
                const propertyDefs = othersModelsInfo[0]?.fieldDefs ?? {};
                for (const propertyName of rest) {
                    const property = propertyDefs[propertyName];
                    if (property?.type === "monetary") {
                        this._addCurrencySpec(spec, property.currency_field);
                    }
                }
                break;
            }
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
                    this._addSpecForFieldPath(spec[field.name].fields, newPathInfo);
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
     */
    async _getReadSpec() {
        const allFieldPaths = await Promise.all(
            [...this.fieldPathsToFetch].map((fieldPath) =>
                this.fieldService.loadPath(this._metaData.resModel, fieldPath),
            ),
        );
        const validFieldPaths = allFieldPaths.filter((result) => !result.isInvalid);
        const spec = {};
        for (const pathInfo of validFieldPaths) {
            this.fieldPathsToFieldMap[pathInfo.names.join(".")] =
                pathInfo.modelsInfo.at(-1).fieldDefs[pathInfo.names.at(-1)];
            this._addSpecForFieldPath(spec, pathInfo);
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
     * @param {string} fieldPath
     * @returns {string | EvaluationError}
     */
    getListHeaderValue(fieldPath) {
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
        const field = this.fieldPathsToFieldMap[fieldPath];
        return field ? field.string : fieldPath;
    }

    /**
     * @returns {object | object[]}
     */
    _getRecordFromRelation(mainRecord, fieldPath) {
        const fields = fieldPath.split(".");
        let record = mainRecord;
        // The last item of fields is the name of the field. As we want to
        // get the record on which the field is defined, we need to iterate until
        // the penultimate item of fields.
        // A property is addressed as `<properties_field>.<property>`, so its
        // two last items both belong to the same record: stop one earlier.
        const isProperty = this.getFieldFromFieldPath(fieldPath)?.is_property;
        const stopAt = fields.length - (isProperty ? 2 : 1);
        for (let i = 0; i < stopAt; i++) {
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
     * @param {string} fieldPath
     * @returns {string|number|undefined|EvaluationError}
     */
    getListCellValue(position, fieldPath) {
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
        if (!this.alreadyFetchedFieldPaths.has(fieldPath)) {
            this.addFieldPathToFetch(fieldPath);
            this._triggerFetching();
            return LOADING_ERROR;
        }
        const field = this.getFieldFromFieldPath(fieldPath);
        if (!field) {
            return new EvaluationError(
                _t(
                    "The field %s does not exist or you do not have access to that field",
                    fieldPath,
                ),
            );
        }
        const mainRecord = this.data[position];
        if (!mainRecord) {
            return "";
        }
        this.assertIsValid();
        const record = this._getRecordFromRelation(mainRecord, fieldPath);
        if (!record) {
            return "";
        }
        if (field.is_property) {
            const names = fieldPath.split(".");
            const propertyName = names.at(-1);
            const properties = record[names.at(-2)] || [];
            const property = properties.find(({ name }) => name === propertyName);
            return property ? this._parsePropertyFieldServerValue(field, property) : "";
        }
        const lastField = fieldPath.split(".").at(-1);
        if (Array.isArray(record)) {
            // remove duplicates?
            // needs to be formatted...
            return record
                .map((r) => this._parseServerValue(field, r[lastField]))
                .join(", ");
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
                const selectedOption = field.selection.find(
                    (array) => array[0] === key,
                );
                return selectedOption ? selectedOption[1] : "";
            }
            case "boolean":
                return value ? true : false;
            case "date":
                return value ? toNumber(this._formatDate(value), DEFAULT_LOCALE) : "";
            case "datetime":
                return value
                    ? toNumber(this._formatDateTime(value), DEFAULT_LOCALE)
                    : "";
            case "properties":
                // Listing the property labels was never useful; a column has to
                // name the property it wants.
                return new EvaluationError(
                    _t("Please specify the property field name"),
                );
            case "json":
                return new EvaluationError(
                    _t('Fields of type "%s" are not supported', "json"),
                );
            case "monetary":
            case "float":
            case "integer":
                return value ?? "";
            default:
                return value || "";
        }
    }

    /**
     * A property is not typed by the `properties` field carrying it but by its
     * own definition, so it is parsed against that instead.
     *
     * @param {object} property the property definition, from `loadPath`
     * @param {object} serverValue `{ type, value }` as read from the server
     */
    _parsePropertyFieldServerValue(property, { type, value }) {
        if (!value) {
            return "";
        }
        switch (type) {
            case "date":
                return toNumber(this._formatDate(value), DEFAULT_LOCALE);
            case "datetime":
                return toNumber(this._formatDateTime(value), DEFAULT_LOCALE);
            case "many2one":
                return value[1];
            case "many2many":
                return value.map(([, displayName]) => displayName).join(", ");
            case "tags":
                return value
                    .map(
                        (tagId) =>
                            property.tags.find(([id]) => id === tagId)?.[1] ?? "",
                    )
                    .join(", ");
            case "selection":
                return property.selection.find(([key]) => key === value)?.[1] ?? "";
            default:
                return value;
        }
    }

    /**
     * @param {number} position
     * @param {string} fieldPath
     * @param {string} currencyFieldName
     * @returns {import("@spreadsheet/currency/plugins/currency").Currency | undefined}
     */
    getListCurrency(position, fieldPath, currencyFieldName) {
        this.assertIsValid();
        const currency = this._getRecordFromRelation(this.data[position], fieldPath)?.[
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

    getFieldFromFieldPath(fieldPath) {
        return this.fieldPathsToFieldMap[fieldPath];
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
                }),
        );
    }
}
