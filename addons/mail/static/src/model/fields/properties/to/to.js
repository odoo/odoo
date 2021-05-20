/** @odoo-module **/

export const to = new Map([
    ['isString', true],
    ['isModelName', true],
    ['requiredProperties', new Set([
        // also required inverse for processed
        new Set(['isX2Many', 'isX2One']),
        new Set(['isMany2X', 'isOne2X']),
    ])],
]);
