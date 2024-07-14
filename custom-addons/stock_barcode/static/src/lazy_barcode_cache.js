/** @odoo-module **/

export default class LazyBarcodeCache {
    constructor(cacheData, params) {
        this.rpc = params.rpc;
        this.dbIdCache = {}; // Cache by model + id
        this.dbBarcodeCache = {}; // Cache by model + barcode
        this.missingBarcode = new Set(); // Used as a cache by `_getMissingRecord`
        this.barcodeFieldByModel = {
            'stock.location': 'barcode',
            'product.product': 'barcode',
            'product.packaging': 'barcode',
            'stock.package.type': 'barcode',
            'stock.picking': 'name',
            'stock.quant.package': 'name',
            'stock.lot': 'name', // Also ref, should take in account multiple fields ?
        };
        this.gs1LengthsByModel = {
            'product.product': 14,
            'product.packaging': 14,
            'stock.location': 13,
            'stock.quant.package': 18,
        };
        // If there is only one active barcode nomenclature, set the cache to be compliant with it.
        if (cacheData['barcode.nomenclature'].length === 1) {
            this.nomenclature = cacheData['barcode.nomenclature'][0];
        }
        this.setCache(cacheData);
    }

    /**
     * Adds records to the barcode application's cache.
     *
     * @param {Object} cacheData each key is a model's name and contains an array of records.
     */
    setCache(cacheData) {
        for (const model in cacheData) {
            const records = cacheData[model];
            // Adds the model's key in the cache's DB.
            if (!this.dbIdCache.hasOwnProperty(model)) {
                this.dbIdCache[model] = {};
            }
            if (!this.dbBarcodeCache.hasOwnProperty(model)) {
                this.dbBarcodeCache[model] = {};
            }
            // Adds the record in the cache.
            const barcodeField = this._getBarcodeField(model);
            for (const record of records) {
                this.dbIdCache[model][record.id] = record;
                if (barcodeField) {
                    const barcode = record[barcodeField];
                    if (!this.dbBarcodeCache[model][barcode]) {
                        this.dbBarcodeCache[model][barcode] = [];
                    }
                    if (!this.dbBarcodeCache[model][barcode].includes(record.id)) {
                        this.dbBarcodeCache[model][barcode].push(record.id);
                        if (this.nomenclature && this.nomenclature.is_gs1_nomenclature && this.gs1LengthsByModel[model]) {
                            this._setBarcodeInCacheForGS1(barcode, model, record);
                        }
                    }
                }
            }
        }
    }

    /**
     * Get record from the cache, throw a error if we don't find in the cache
     * (the server should have return this information).
     *
     * @param {int} id id of the record
     * @param {string} model model_name of the record
     * @param {boolean} [copy=true] if true, returns a deep copy (to avoid to write the cache)
     * @returns copy of the record send by the server (fields limited to _get_fields_stock_barcode)
     */
    getRecord(model, id) {
        if (!this.dbIdCache.hasOwnProperty(model)) {
            throw new Error(`Model ${model} doesn't exist in the cache`);
        }
        if (!this.dbIdCache[model].hasOwnProperty(id)) {
            throw new Error(`Record ${model} with id=${id} doesn't exist in the cache, it should return by the server`);
        }
        const record = this.dbIdCache[model][id];
        return JSON.parse(JSON.stringify(record));
    }

    /**
     * @param {string} barcode barcode to match with a record
     * @param {string} [model] model name of the record to match (if empty search on all models)
     * @param {boolean} [onlyInCache] search only in the cache
     * @param {Object} [filters]
     * @returns copy of the record send by the server (fields limited to _get_fields_stock_barcode)
     */
    async getRecordByBarcode(barcode, model = false, onlyInCache = false, filters = {}) {
        if (model) {
            if (!this.dbBarcodeCache.hasOwnProperty(model)) {
                throw new Error(`Model ${model} doesn't exist in the cache`);
            }
            if (!this.dbBarcodeCache[model].hasOwnProperty(barcode)) {
                if (onlyInCache) {
                    return null;
                }
                await this._getMissingRecord(barcode, model, filters);
                return await this.getRecordByBarcode(barcode, model, true, filters);
            }
            const ids = this.dbBarcodeCache[model][barcode];
            for (const id of ids) {
                const record = this.getRecord(model, id);
                let pass = true;
                if (filters[model]) {
                    const fields = Object.keys(filters[model]);
                    for (const field of fields) {
                        if (record[field] != filters[model][field]) {
                            pass = false;
                            break;
                        }
                    }
                }
                if (pass) {
                    return record;
                }
            }
        } else {
            const result = new Map();
            // Returns object {model: record} of possible record.
            const models = Object.keys(this.dbBarcodeCache);
            for (const model of models) {
                if (this.dbBarcodeCache[model].hasOwnProperty(barcode)) {
                    const ids = this.dbBarcodeCache[model][barcode];
                    for (const id of ids) {
                        const record = this.dbIdCache[model][id];
                        let pass = true;
                        if (filters[model]) {
                            const fields = Object.keys(filters[model]);
                            for (const field of fields) {
                                if (record[field] != filters[model][field]) {
                                    pass = false;
                                    break;
                                }
                            }
                        }
                        if (pass) {
                            result.set(model, JSON.parse(JSON.stringify(record)));
                            break;
                        }
                    }
                }
            }
            if (result.size < 1) {
                if (onlyInCache) {
                    return result;
                }
                await this._getMissingRecord(barcode, model, filters);
                return await this.getRecordByBarcode(barcode, model, true, filters);
            }
            return result;
        }
    }

    _getBarcodeField(model) {
        if (!this.barcodeFieldByModel.hasOwnProperty(model)) {
            return null;
        }
        return this.barcodeFieldByModel[model];
    }

    async _getMissingRecord(barcode, model, filters = {}) {
        const keyCache = JSON.stringify([...arguments]);
        const missCache = this.missingBarcode;
        const params = { barcode, model_name: model };
        // Check if we already try to fetch this missing record.
        if (missCache.has(keyCache)) {
            return false;
        }
        // Creates and passes a domain if some filters are provided.
        const domainsByModel = {};
        for (const filter of Object.entries(filters)) {
            const modelName = filter[0];
            const filtersByField = filter[1];
            domainsByModel[modelName] = [];
            for (const filterByField of Object.entries(filtersByField)) {
                domainsByModel[modelName].push([filterByField[0], '=', filterByField[1]]);
            }
        }
        params.domains_by_model = domainsByModel;
        const result = await this.rpc('/stock_barcode/get_specific_barcode_data', params);
        this.setCache(result);
        missCache.add(keyCache);
    }

    /**
     * Sets in the cache an entry for the given record with its formatted barcode as key.
     * The barcode will be formatted (if needed) at the length corresponding to its data part in a
     * GS1 barcode (e.g.: 14 digits for a product's barcode) by padding with 0 the original barcode.
     * That makes it easier to find when a GS1 barcode is scanned.
     * If the formatted barcode is similar to an another barcode for the same model, it will show a
     * warning in the console (as a clue to find where issue could come from, not to alert the user)
     *
     * @param {string} barcode
     * @param {string} model
     * @param {Object} record
     */
    _setBarcodeInCacheForGS1(barcode, model, record) {
        const length = this.gs1LengthsByModel[model];
        if (!barcode || barcode.length >= length || isNaN(Number(barcode))) {
            // Barcode already has the good length, or is too long or isn't
            // fully numerical (and so, it doesn't make sense to adapt it).
            return;
        }
        const paddedBarcode = barcode.padStart(length, '0');
        // Avoids to override or mix records if there is already a key for this
        // barcode (which means there is a conflict somewhere).
        if (!this.dbBarcodeCache[model][paddedBarcode]) {
            this.dbBarcodeCache[model][paddedBarcode] = [record.id];
        } else if (!this.dbBarcodeCache[model][paddedBarcode].includes(record.id)) {
            const previousRecordId = this.dbBarcodeCache[model][paddedBarcode][0];
            const previousRecord = this.getRecord(model, previousRecordId);
            console.log(
                `Conflict for barcode %c${paddedBarcode}%c:`, 'font-weight: bold', '',
                `it could refer for both ${record.display_name} and ${previousRecord.display_name}.`,
                `\nThe last one will be used but consider to edit those products barcode to avoid error due to ambiguities.`
            );
        }
    }
}
