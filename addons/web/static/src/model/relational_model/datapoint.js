import { markRaw } from "@odoo/owl";
import { evalDomain } from "@web/core/domain";
import { Reactive } from "@web/core/utils/reactive";
import { getId } from "./utils";

/**
 * @typedef Params
 * @property {string} resModel
 * @property {Object} context
 * @property {{[key: string]: FieldInfo}} activeFields
 * @property {{[key: string]: Field}} fields
 */

/**
 * @typedef Field
 * @property {string} name
 * @property {string} type
 * @property {[string,string][]} [selection]
 */

/**
 * @typedef FieldInfo
 * @property {string} context
 * @property {boolean} invisible
 * @property {boolean} readonly
 * @property {boolean} required
 * @property {boolean} onChange
 */

export class DataPoint extends Reactive {
    /**
     * @param {import("./relational_model").RelationalModel} model
     * @param {import("./relational_model").Config"} config
     * @param {any} data
     * @param {Object} [options]
     */
    constructor(model, config, data, options) {
        super(...arguments);
        this.id = getId("datapoint");
        this.model = model;
        markRaw(config.activeFields);
        markRaw(config.fields);
        this._config = config;
        this.setup(config, data, options);
    }

    /**
     * @abstract
     * @param {Object} params
     * @param {Object} state
     */
    setup() {}

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

    get currentCompanyId() {
        return this.config.currentCompanyId;
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * @param {string} fieldName
     * @returns {boolean}
     */
    isFieldReadonly(fieldName) {
        const activeField = this.activeFields[fieldName];
        const { readonly } = activeField || this.fields[fieldName];
        return readonly && evalDomain(readonly, this.evalContext);
    }
}
