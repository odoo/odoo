/** @odoo-module **/

export const standardFieldProps = {
    archs: { type: [Object, false], optional: true },
    id: { type: String, optional: true },
    name: String,
    readonly: Boolean,
    required: Boolean,
    record: Object,
    type: String,
    update: Function,
    value: true,
};
