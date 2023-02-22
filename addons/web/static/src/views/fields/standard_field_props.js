/** @odoo-module **/

export const standardFieldProps = {
    id: { type: String, optional: true },
    name: { type: String, optional: true },
    readonly: { type: Boolean, optional: true },
    record: { type: Object },
    value: true,
    decorations: { type: Object, optional: true },
    setDirty: { type: Function, optional: true },
};
