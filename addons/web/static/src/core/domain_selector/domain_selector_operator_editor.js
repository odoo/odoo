function getSpecificOperators(fieldDef, params) {
    const { type, is_property } = fieldDef;

    if (is_property) {
        switch (type) {
            case "many2many":
            case "tags":
            case "many2one":
                return [];
        }
    }
    const allowExpressions = "allowExpressions" in params ? params.allowExpressions : true;
    switch (type) {
        case "char":
        case "text":
        case "html":
        case "many2one":
        case "many2many":
        case "one2many":
            return ["ilike", "not ilike", "starts_with", "ends_with"];
        case "date":
        case "datetime":
            return [
                ...(allowExpressions ? ["today", "not_today"] : []),
                ">",
                "<",
                "between",
                "not_between",
                ...(allowExpressions ? ["next", "not_next", "last", "not_last"] : []),
            ];
        case "integer":
        case "float":
        case "monetary":
            return [">", "<", "between", "not_between", "ilike", "not ilike"];
        case "json":
            return ["ilike", "not ilike"];
        case "date_option":
        case "time_option":
        case "datetime_option":
            return [">", "<", "between", "not_between"];
        default:
            return [];
    }
}

export function getDomainDisplayedOperators(fieldDef, params = {}) {
    fieldDef ||= {};
    if (!fieldDef.type) {
        return ["="];
    }
    if (fieldDef.type === "boolean") {
        return ["set", "not_set"];
    }
    return ["in", "not in", ...getSpecificOperators(fieldDef, params), "set", "not_set"];
}
