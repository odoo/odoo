/** @odoo-module **/

export const standardFieldProps = {
    id: { type: String, optional: true },
    name: { type: String, optional: true },
    readonly: { type: Boolean, optional: true },
    record: { type: Object, optional: true },
    type: { type: String, optional: true },
    update: { type: Function, optional: true },
    value: true,
    decorations: { type: Object, optional: true },
    setDirty: { type: Function, optional: true },
};
