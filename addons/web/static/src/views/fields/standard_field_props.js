/** @odoo-module **/

/**
 * @typedef StandardFieldProps
 * @property {string} [id]
 * @property {string} name
 * @property {boolean} [readonly]
 * @property {import("@web/views/relational_model").Record} record
 */

export const standardFieldProps = {
    id: { type: String, optional: true },
    name: { type: String },
    readonly: { type: Boolean, optional: true },
    record: { type: Object },
};
