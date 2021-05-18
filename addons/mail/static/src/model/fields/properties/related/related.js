/** @odoo-module **/

import { checkRelatedProperty as checkDeclaration } from '@mail/model/fields/properties/related/check_related_property';

export const related = {
    checkDeclaration,
    excludedProperties: [],
    isRequired: false,
    requiredProperties: ['compute'],
};
