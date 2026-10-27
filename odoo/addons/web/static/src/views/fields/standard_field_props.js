/** @odoo-module **/

/**
 * @typedef StandardFieldProps
 * @property {string} [id]
 * @property {string} name
 * @property {boolean} [readonly]
 * @property {import("@web/model/relational_model/record").Record} record
 */

export const standardFieldProps = {
    id: { type: String, optional: true },
    name: { type: String },
    readonly: { type: Boolean, optional: true },
    record: { type: Object },
};
