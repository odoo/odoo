// @ts-check

/** @module @web/fields/standard_field_props - Standard OWL props schema shared by all field widget components */

/**
 * @typedef StandardFieldProps
 * @property {string} [id]
 * @property {string} name
 * @property {boolean} [readonly]
 * @property {import("@web/model/relational_model/record").RelationalRecord} record
 */

export const standardFieldProps = {
    id: { type: String, optional: true },
    name: { type: String },
    readonly: { type: Boolean, optional: true },
    record: { type: Object },
};
