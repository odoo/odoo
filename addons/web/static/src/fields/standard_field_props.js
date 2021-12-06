/** @odoo-module **/

export const standardFieldProps = {
    archs: { type: [Object, false], optional: true },
    attrs: Object,
    id: { type: String, optional: true },
    name: String,
    options: Object,
    readonly: Boolean,
    required: Boolean,
    record: Object,
    type: String,
    update: Function,
    value: true,
    decorations: { type: Object, optional: true },
    formatValue: Function,
    parseValue: Function,
};
