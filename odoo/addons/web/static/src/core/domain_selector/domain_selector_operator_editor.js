/** @odoo-module **/

export function getDomainDisplayedOperators(fieldDef) {
    if (!fieldDef) {
        fieldDef = {};
    }
    const { type, is_property } = fieldDef;

    if (is_property) {
        switch (type) {
            case "many2many":
            case "tags":
                return ["in", "not in", "set", "not_set"];
            case "many2one":
            case "selection":
                return ["=", "!=", "set", "not_set"];
        }
    }

    switch (type) {
        case "boolean":
            return ["is", "is_not"];
        case "selection":
            return ["=", "!=", "in", "not in", "set", "not_set"];
        case "char":
        case "text":
        case "html":
            return ["=", "!=", "ilike", "not ilike", "in", "not in", "set", "not_set"];
        case "date":
        case "datetime":
            return ["=", "!=", ">", ">=", "<", "<=", "between", "set", "not_set"];
        case "integer":
        case "float":
        case "monetary":
            return [
                "=",
                "!=",
                ">",
                ">=",
                "<",
                "<=",
                "between",
                "ilike",
                "not ilike",
                "set",
                "not_set",
            ];
        case "many2one":
        case "many2many":
        case "one2many":
            return ["in", "not in", "=", "!=", "ilike", "not ilike", "set", "not_set"];
        case "json":
            return ["=", "!=", "ilike", "not ilike", "set", "not_set"];
        case "properties":
            return ["set", "not_set"];
        case undefined:
            return ["="];
        default:
            return [
                "=",
                "!=",
                ">",
                ">=",
                "<",
                "<=",
                "ilike",
                "not ilike",
                "like",
                "not like",
                "=like",
                "=ilike",
                "child_of",
                "parent_of",
                "in",
                "not in",
                "set",
                "not_set",
            ];
    }
}
