/** @odoo-module **/

export const attribute = new Map([
    ['nameOfAvailableProperties', new Set([
        'compute',
        'default',
        'dependencies',
        'fieldName',
        'isOnChange',
        'readonly',
        'related',
        'required',
    ])],
    ['nameOfRequiredProperties', new Set([
        'fieldName',
    ])],
]);
