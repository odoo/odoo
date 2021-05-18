/** @odoo-module **/

import { compute } from '@mail/model/fields/properties/compute/compute';
import { defaultProperty } from '@mail/model/fields/properties/default/default';
import { dependencies } from '@mail/model/fields/properties/dependencies/dependencies';
import { fieldName } from '@mail/model/fields/properties/field_name/field_name';
import { fieldType } from '@mail/model/fields/properties/field_type/field_type';
import { related } from '@mail/model/fields/properties/related/related';
import { checkRelationField as checkDeclaration } from '@mail/model/fields/types/relation/check_relation_field';

export const relation = {
    checkDeclaration,
    fieldPropertyRegistry: new Map([
        ['fieldName', fieldName],
        ['fieldType', fieldType],
        ['compute', compute],
        ['default', defaultProperty],
        ['dependencies', dependencies],
        ['inverse', { checkDeclaration: () => {} }],
        ['isCausal', { checkDeclaration: () => {} }],
        ['readonly', { checkDeclaration: () => {} }],
        ['related', related],
        ['relationType', { checkDeclaration: () => {} }],
        ['required', { checkDeclaration: () => {} }],
        ['to', { checkDeclaration: () => {} }],
    ]),
};
