/** @odoo-module **/

export const related = new Map([
    ['isString', true],
    ['isStringWithTwoPartsSeparatedByDot', true],
    ['isRelationNameDotFieldName', true],
    ['excludedProperties', new Set(['compute'])],
    // TODO SEB need to define the list of what properties must be present (or must not be present?) on the relation field and on the target field
]);
