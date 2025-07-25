export function getDomainDisplayedOperators(fieldDef) {
    if (!fieldDef) {
        fieldDef = {};
    }
    const { type, is_property } = fieldDef;

    if (is_property) {
        switch (type) {
            case "many2many":
            case "tags":
                return ["in", "not in", "set", "not set"];
            case "many2one":
            case "selection":
                return ["=", "!=", "set", "not set"];
        }
    }
    switch (type) {
        case "boolean":
            return ["set", "not set"];
        case "selection":
            return ["=", "!=", "in", "not in", "set", "not set"];
        case "char":
        case "text":
        case "html":
            return ["=", "!=", "ilike", "not ilike", "starts with", "set", "not set"];
        case "date":
        case "datetime":
            return ["in range", "=", "<", ">", "set", "not set"];
        case "integer":
        case "float":
        case "monetary":
            return ["=", "!=", "<", ">", "between"];
        case "many2one":
        case "many2many":
        case "one2many":
            return ["in", "not in", "ilike", "not ilike", "set", "not set"];
        case "json":
            return ["=", "!=", "ilike", "not ilike", "set", "not set"];
        case "binary":
        case "properties":
            return ["set", "not set"];
        case undefined:
            return ["="];
        default:
            return [
                "=",
                "!=",
                "<",
                ">",
                "ilike",
                "not ilike",
                "like",
                "not like",
                "=like",
                "=ilike",
                "in",
                "not in",
                "set",
                "not set",
            ];
    }
}
