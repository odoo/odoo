/**
 * The value of a field as text, whatever its type: for fields that have no
 * component yet.
 *
 * Values without a text form (binary content, json, properties) are not
 * displayed.
 *
 * @param {any} value what the field signal of a record returns
 * @param {{ type: string; selection?: [string, string][] }} field
 *  description of the field, from the view
 * @returns {string}
 */
export function displayValue(value, field) {
    switch (field.type) {
        case "many2one":
            return value ? value.display_name() : "";
        case "one2many":
        case "many2many":
            return (value || []).map((record) => record.display_name()).join(", ");
        case "selection":
            return field.selection?.find(([key]) => key === value)?.[1] ?? (value || "");
        case "binary":
        case "json":
        case "properties":
        case "properties_definition":
            return "";
        default:
            return value === false || value === null || value === undefined ? "" : String(value);
    }
}
