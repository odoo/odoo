/** @odoo-module **/

export const standardFieldProps = {
    archs: { type: [Object, false], optional: true },
    id: { type: String, optional: true },
    meta: Object,
    name: String,
    readonly: Boolean,
    readonlyFromModifier: Boolean,
    readonlyFromView: Boolean,
    required: Boolean,
    record: Object,
    type: String,
    update: Function,
    value: true,
};
