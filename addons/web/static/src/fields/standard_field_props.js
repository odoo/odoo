/** @odoo-module **/

export const standardFieldProps = {
    archs: { type: [Object, false], optional: true }, // FIXME WOWL remove this
    id: { type: String, optional: true },
    name: String,
    readonly: Boolean,
    required: Boolean,
    record: Object,
    type: String,
    update: Function,
    value: true,
    decorations: { type: Object, optional: true },
};
