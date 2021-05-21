/** @odoo-module **/

export const isCausal = new Map([
    ['excludedProperties', new Set(['isMany2X'])],
    ['requiredProperties', new Set(['isOne2X'])],
    ['isBoolean', true],
]);
