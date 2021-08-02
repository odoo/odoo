/** @odoo-module */

import { Field } from "../../fields/field";
import { evaluateExpr } from "../../core/py_js/py";

const RELATIONAL_TYPES = ["one2many", "many2many"];
const SPECIAL_FIELDS = {
    color_field: { type: "integer" },
};

export const isRelational = (field) => field && RELATIONAL_TYPES.includes(field.type);

export class FieldParser {
    /**
     * @param {any} fields
     * @param {string[]} defaultFields
     */
    constructor(fields) {
        this.fields = fields;
        this.parsedFields = Object.create(null);
        this.relations = {};
    }

    /**
     * @param {Element} node
     * @param {(fieldName: string) => any} [getFieldInfo=(fieldName)=>fieldName]
     * @returns {{ name: string, field: any, widget: string | false }}
     */
    addField(node, getFieldInfo) {
        const fieldName = node.getAttribute("name");
        const widget = node.getAttribute("widget");
        const field = this.fields[fieldName];
        this.parsedFields[fieldName] = getFieldInfo ? getFieldInfo(fieldName) : fieldName;
        if (isRelational(field)) {
            const relatedFields = {};
            const options = evaluateExpr(node.getAttribute("options") || "{}");
            const FieldClass = Field.getTangibleField({ fields: this.fields }, widget, fieldName);
            if (FieldClass.fieldsToFetch) {
                Object.assign(relatedFields, FieldClass.fieldsToFetch);
            }
            for (const specialFieldDef in SPECIAL_FIELDS) {
                const specialFieldName = options[specialFieldDef];
                if (specialFieldName) {
                    relatedFields[specialFieldName] = SPECIAL_FIELDS[specialFieldDef];
                }
            }
            if (Object.keys(relatedFields).length) {
                if (!(field.relation in this.relations)) {
                    this.relations[field.relation] = {};
                }
                Object.assign(this.relations[field.relation], relatedFields);
            }
        }
        return { name: fieldName, field, widget };
    }

    getFields() {
        return Object.values(this.parsedFields);
    }

    getRelations() {
        return this.relations;
    }
}
