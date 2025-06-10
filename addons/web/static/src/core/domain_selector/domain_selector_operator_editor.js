export function getDomainDisplayedOperators(fieldDef, params = {}) {
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
            return ["set", "not_set"];
        case "selection":
            return ["=", "!=", "in", "not in", "set", "not_set"];
        case "char":
        case "text":
        case "html":
            return [
                "=",
                "!=",
                "ilike",
                "not ilike",
                "in",
                "not in",
                "set",
                "not_set",
                "starts_with",
                "ends_with",
            ];
        case "date":
        case "datetime":
            return [
                ...("allowExpressions" in params && !params.allowExpressions
                    ? []
                    : ["today", "not_today"]),
                "=",
                "!=",
                ">",
                "<",
                "between",
                "not_between",
                ...("allowExpressions" in params && !params.allowExpressions
                    ? []
                    : ["next", "not_next", "last", "not_last"]),
                "set",
                "not_set",
            ];
        case "integer":
        case "float":
        case "monetary":
            return [
                "=",
                "!=",
                ">",
                "<",
                "between",
                "not_between",
                "ilike",
                "not ilike",
                "set",
                "not_set",
            ];
        case "many2one":
        case "many2many":
        case "one2many":
            return [
                "in",
                "not in",
                "=",
                "!=",
                "ilike",
                "not ilike",
                "set",
                "not_set",
                "starts_with",
                "ends_with",
            ];
        case "json":
            return ["=", "!=", "ilike", "not ilike", "set", "not_set"];
        case "binary":
        case "properties":
            return ["set", "not_set"];
        case "date_option":
        case "datetime_option":
        case "time_option":
            return ["=", "!=", ">", "<", "between", "not_between", "set", "not_set"];
        case undefined:
            return ["="];
        default:
            return [
                "=",
                "!=",
                ">",
                "<",
                "ilike",
                "not ilike",
                "like",
                "not like",
                "=like",
                "=ilike",
                "in",
                "not in",
                "set",
                "not_set",
            ];
    }
}
