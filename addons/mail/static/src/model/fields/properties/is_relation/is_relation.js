/** @odoo-module **/

export const isRelation = new Map([
    ['excludedProperties', new Set(['isOnChange'])],
    ['requiredProperties', new Set([
        'to',
        new Set(['isX2Many', 'isX2One']),
        new Set(['isMany2X', 'isOne2X']),
    ])],
    // also required inverse for processed
]);
