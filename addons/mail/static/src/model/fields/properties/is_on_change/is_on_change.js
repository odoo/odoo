/** @odoo-module **/

import { checkIsOnChangeProperty as checkDeclaration } from '@mail/model/fields/properties/is_on_change/check_isonchange_property';

export const isOnChange = {
    checkDeclaration,
    excludedProperties: [],
    isRequired: false,
    requiredProperties: ['compute'],
};
