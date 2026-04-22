import { markRaw, signal } from "@odoo/owl";
import { getId } from "./utils";

/**
 * @template T
 * @param {T} target
 * @param {keyof T} name
 * @param {typeof signal} signalFn
 */
export function makeReactive(target, name, signalFn) {
    const _signal = signalFn(target[name]);
    Object.defineProperty(target, name, {
        get: _signal,
        set: _signal.set,
    });
}

/**
 * @typedef {import("@web/search/search_model").Field} Field
 * @typedef {import("@web/search/search_model").FieldInfo} FieldInfo
 * @typedef {import("./relational_model").RelationalModel} RelationalModel
 * @typedef {import("./relational_model").RelationalModelConfig} RelationalModelConfig
 */

export class DataPoint {
    /**
     * @param {RelationalModel} model
     * @param {RelationalModelConfig} config
     * @param {Record<string, unknown>} data
     * @param {unknown} [options]
     */
    constructor(model, config, data, options) {
        this.id = getId("datapoint");
        this.model = model;
        markRaw(config.activeFields);
        markRaw(config.fields);

        /** @type {RelationalModelConfig} */
        this._config = config;

        this.setup(config, data, options);

        makeReactive(this, "_config", signal.Object);
    }

    /**
     * @abstract
     * @template [O={}]
     * @param {RelationalModelConfig} _config
     * @param {Record<string, unknown>} _data
     * @param {O | undefined} _options
     */
    setup(_config, _data, _options) {}

    get activeFields() {
        return this.config.activeFields;
    }

    get fields() {
        return this.config.fields;
    }

    get fieldNames() {
        return Object.keys(this.activeFields).filter(
            (fieldName) => !this.fields[fieldName].relatedPropertyField
        );
    }

    get resModel() {
        return this.config.resModel;
    }

    get config() {
        return this._config;
    }

    get context() {
        return this.config.context;
    }
}
