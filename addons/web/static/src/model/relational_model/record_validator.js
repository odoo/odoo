// @ts-check

/** @module @web/model/relational_model/record_validator - Pure validation logic to find unset required fields in a record */

/**
 * Pure validation logic for Record field values.
 *
 * Determines which required fields are unset without mutating any state.
 * The caller (Record._checkValidity) handles state updates, notifications,
 * and recursive child record validation via the `isChildListValid` callback.
 */

/**
 * Determine which required fields in a record are unset or invalid.
 *
 * Iterates all active fields, skipping invisible and property-derived fields,
 * and checks each field type for "unset" conditions (empty string for html,
 * zero count for x2many, etc.).
 *
 * @param {Object} activeFields
 * @param {Object} fields - field definitions
 * @param {Object} data - current record data
 * @param {Object} callbacks
 * @param {(fieldName: string) => boolean} callbacks.isInvisible
 * @param {(fieldName: string) => boolean} callbacks.isRequired
 * @param {(fieldName: string, list: Object) => boolean} callbacks.isChildListValid
 *     Validates x2many child records. Called with the field name and the
 *     StaticList datapoint. Should return true if all child records are valid.
 * @returns {Set<string>} field names of unset required fields
 */
export function findUnsetRequiredFields(
    activeFields,
    fields,
    data,
    { isInvisible, isRequired, isChildListValid },
) {
    const unsetRequiredFields = new Set();
    for (const fieldName in activeFields) {
        const fieldType = fields[fieldName].type;
        if (isInvisible(fieldName) || fields[fieldName].relatedPropertyField) {
            continue;
        }
        switch (fieldType) {
            case "boolean":
            case "float":
            case "integer":
            case "monetary":
                continue;
            case "html":
                if (isRequired(fieldName) && data[fieldName].length === 0) {
                    unsetRequiredFields.add(fieldName);
                }
                break;
            case "one2many":
            case "many2many": {
                const list = data[fieldName];
                if (
                    (isRequired(fieldName) && !list.count) ||
                    !isChildListValid(fieldName, list)
                ) {
                    unsetRequiredFields.add(fieldName);
                }
                break;
            }
            case "properties": {
                const value = data[fieldName];
                if (value) {
                    const ok = value.every(
                        (propertyDefinition) =>
                            propertyDefinition.name &&
                            propertyDefinition.name.length &&
                            propertyDefinition.string &&
                            propertyDefinition.string.length,
                    );
                    if (!ok) {
                        unsetRequiredFields.add(fieldName);
                    }
                }
                break;
            }
            case "json": {
                const value = data[fieldName];
                const jsonEmpty =
                    value == null ||
                    (typeof value === "object" && Object.keys(value).length === 0);
                if (isRequired(fieldName) && jsonEmpty) {
                    unsetRequiredFields.add(fieldName);
                }
                break;
            }
            default:
                if (!data[fieldName] && isRequired(fieldName)) {
                    unsetRequiredFields.add(fieldName);
                }
        }
    }
    return unsetRequiredFields;
}
