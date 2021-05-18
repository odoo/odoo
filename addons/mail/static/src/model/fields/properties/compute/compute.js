/** @odoo-module **/

import { checkComputeProperty as checkDeclaration } from '@mail/model/fields/properties/compute/check_compute_property';

export const compute = {
    checkDeclaration,
    excludedProperties: ['related'],
    isRequired: false,
    requiredProperties: [],
};
