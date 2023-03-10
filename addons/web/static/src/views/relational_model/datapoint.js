/* @odoo-module */

import { markup } from "@odoo/owl";
import { deserializeDate, deserializeDateTime } from "@web/core/l10n/dates";

let nextId = 0;
export class DataPoint {
    /**
     * @param {RelationalModel} model
     * @param {Object} [params={}]
     * @param {Object} [state={}]
     */
    constructor(model, params = {}, state = {}) {
        this.id = `datapoint_${nextId++}`;
        this.model = model;
        this.resModel = params.resModel;
        this.context = params.context;
        this.fields = {
            id: { name: "id", type: "integer", readonly: true },
            display_name: { name: "display_name", type: "char" },
            ...params.fields,
        };
        this.activeFields = params.activeFields;
        this.fieldNames = Object.keys(this.activeFields);
        this.setup(params, state);
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * @abstract
     * @param {Object} params
     * @param {Object} state
     */
    setup() {}

    // FIXME: not sure we want to keep this mecanism
    exportState() {}

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    _parseServerValue(field, value) {
        if (!field) {
            field = { type: "integer" };
        }
        switch (field.type) {
            case "char":
            case "text": {
                return value || "";
            }
            case "date": {
                return value ? deserializeDate(value) : false;
            }
            case "datetime": {
                return value ? deserializeDateTime(value) : false;
            }
            case "html": {
                return markup(value || "");
            }
            case "selection": {
                if (value === false) {
                    // process selection: convert false to 0, if 0 is a valid key
                    const hasKey0 = field.selection.find((option) => option[0] === 0);
                    return hasKey0 ? 0 : value;
                }
                return value;
            }
            case "one2many":
            case "many2many": {
                const related = this.activeFields[field.name].related;
                return new this.model.constructor.StaticList(this.model, {
                    // FIXME: can't do that here, no context...
                    resModel: field.relation,
                    activeFields: (related && related.activeFields) || {},
                    fields: (related && related.fields) || {},
                    data: value,
                });
            }
        }
        return value;
    }

    _parseServerValues(values) {
        const parsedValues = {};
        if (!values) {
            return parsedValues;
        }
        for (const fieldName in values) {
            const value = values[fieldName];
            const field = this.fields[fieldName];
            parsedValues[fieldName] = this._parseServerValue(field, value);
        }
        return parsedValues;
    }
}
