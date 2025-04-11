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
    const hierarchyOperators = fieldDef.allow_hierachy_operators ? ["child_of", "parent_of"] : [];
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
                "today",
                "not_today",
                "=",
                "!=",
                ">",
                ">=",
                "<",
                "<=",
                "between",
                "is_not_between",
                "next",
                "not_next",
                "last",
                "not_last",
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
                ">=",
                "<",
                "<=",
                "between",
                "is_not_between",
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
                ...hierarchyOperators,
                "set",
                "not_set",
                "starts_with",
                "ends_with",
                "any",
                "not any",
            ];
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
                "in",
                "not in",
                "set",
                "not_set",
            ];
    }
}
