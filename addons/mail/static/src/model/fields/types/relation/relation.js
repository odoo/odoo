/** @odoo-module **/

export const relation = new Map([
    ['nameOfAvailableProperties', new Set([
        'compute',
        'default',
        'dependencies',
        'inverse',
        'isCausal',
        'isMany2X',
        'isOne2X',
        'isX2Many',
        'isX2One',
        'readonly',
        'related',
        'required',
        'to',
    ])],
    ['nameOfRequiredProperties', new Set([
        'to',
    ])],
]);
