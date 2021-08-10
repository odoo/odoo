/** @odoo-module */

import { Field } from "../../fields/field";
import { evaluateExpr } from "../../core/py_js/py";

const RELATIONAL_TYPES = ["many2one", "one2many", "many2many"];
const SPECIAL_FIELDS = ["color_field"];

export const isRelational = (field) => field && RELATIONAL_TYPES.includes(field.type);

export const getIds = (idsList) => {
    if (Array.isArray(idsList)) {
        if (idsList.length === 2 && typeof idsList[1] === "string") {
            return [idsList[0]];
        } else {
            return idsList;
        }
    } else if (idsList) {
        return [idsList];
    } else {
        return [];
    }
};

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
        const options = evaluateExpr(node.getAttribute("options") || "{}");
        this.parsedFields[fieldName] = getFieldInfo ? getFieldInfo(fieldName) : fieldName;
        if (isRelational(field)) {
            const relatedFields = [];
            const FieldClass = Field.getTangibleField({ fields: this.fields }, widget, fieldName);
            if (FieldClass.fieldsToFetch) {
                relatedFields.push(...FieldClass.fieldsToFetch);
            }
            for (const specialFieldDef of SPECIAL_FIELDS) {
                const specialFieldName = options[specialFieldDef];
                if (specialFieldName) {
                    relatedFields.push(specialFieldName);
                }
            }
            this.addRelation(field.relation, ...relatedFields);
        }
        return { name: fieldName, field, widget, options };
    }

    /**
     * @param {string} relation
     * @param  {...string} fields
     */
    addRelation(relation, ...fields) {
        if (!fields.length) {
            return;
        }
        if (!(relation in this.relations)) {
            this.relations[relation] = new Set();
        }
        for (const field of fields) {
            this.relations[relation].add(field);
        }
    }

    getFields() {
        return Object.values(this.parsedFields);
    }

    getRelations() {
        const relations = {};
        for (const fieldName in this.relations) {
            relations[fieldName] = [...this.relations[fieldName]];
        }
        return relations;
    }
}
