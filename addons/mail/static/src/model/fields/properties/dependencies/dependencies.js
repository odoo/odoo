/** @odoo-module **/

import { checkDependenciesProperty as checkDeclaration } from '@mail/model/fields/properties/dependencies/check_dependencies_property';

export const dependencies = {
    checkDeclaration,
    excludedProperties: [],
    isRequired: false,
    requiredProperties: ['compute'],
};
