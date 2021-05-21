/** @odoo-module **/

export const to = new Map([
    ['requiredProperties', new Set([
        new Set(['isX2Many', 'isX2One']),
        new Set(['isMany2X', 'isOne2X']),
    ])],
    ['isString', true],
    ['isModelName', true],
]);
