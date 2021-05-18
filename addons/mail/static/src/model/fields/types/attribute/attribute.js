/** @odoo-module **/

import { compute } from '@mail/model/fields/properties/compute/compute';
import { defaultProperty } from '@mail/model/fields/properties/default/default';
import { dependencies } from '@mail/model/fields/properties/dependencies/dependencies';
import { fieldName } from '@mail/model/fields/properties/field_name/field_name';
import { fieldType } from '@mail/model/fields/properties/field_type/field_type';
import { isOnChange } from '@mail/model/fields/properties/is_on_change/is_on_change';
import { related } from '@mail/model/fields/properties/related/related';
import { checkAttributeField as checkDeclaration } from '@mail/model/fields/types/attribute/check_attribute_field';

export const attribute = {
    checkDeclaration,
    fieldPropertyRegistry: new Map([
        ['fieldName', fieldName],
        ['fieldType', fieldType],
        ['compute', compute],
        ['default', defaultProperty],
        ['dependencies', dependencies],
        ['isOnChange', isOnChange],
        ['readonly', { checkDeclaration: () => {} }],
        ['related', related],
        ['required', { checkDeclaration: () => {} }],
    ]),
};
