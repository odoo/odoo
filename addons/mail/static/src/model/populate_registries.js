/** @odoo-module **/

import { compute } from '@mail/model/fields/properties/compute/compute';
import { defaultProperty } from '@mail/model/fields/properties/default/default';
import { dependencies } from '@mail/model/fields/properties/dependencies/dependencies';
import { inverse } from '@mail/model/fields/properties/inverse/inverse';
import { isCausal } from '@mail/model/fields/properties/is_causal/is_causal';
import { isMany2X } from '@mail/model/fields/properties/is_many2x/is_many2x';
import { isOnChange } from '@mail/model/fields/properties/is_on_change/is_on_change';
import { isOne2X } from '@mail/model/fields/properties/is_one2x/is_one2x';
import { isX2Many } from '@mail/model/fields/properties/is_x2many/is_x2many';
import { isX2One } from '@mail/model/fields/properties/is_x2one/is_x2one';
import { readonly } from '@mail/model/fields/properties/readonly/readonly';
import { related } from '@mail/model/fields/properties/related/related';
import { required } from '@mail/model/fields/properties/required/required';
import { to } from '@mail/model/fields/properties/to/to';
import { attribute } from '@mail/model/fields/types/attribute/attribute';
import { relation } from '@mail/model/fields/types/relation/relation';

/**
 * Populate registries with models, fields, and properties expected by the app.
 *
 * @param {Object} param0
 * @param {Object} param0.env
 */
export function populateRegistries(env) {
    const properties = [
        ['compute', compute],
        ['default', defaultProperty],
        ['dependencies', dependencies],
        ['inverse', inverse],
        ['isCausal', isCausal],
        ['isMany2X', isMany2X],
        ['isOnChange', isOnChange],
        ['isOne2X', isOne2X],
        ['isX2Many', isX2Many],
        ['isX2One', isX2One],
        ['readonly', readonly],
        ['related', related],
        ['required', required],
        ['to', to],
    ];
    for (const [name, property] of properties) {
        env.modelManager.fieldPropertyRegistry.set(name, property);
    }
    const types = [
        ['attribute', attribute],
        ['relation', relation],
    ];
    for (const [name, type] of types) {
        env.modelManager.fieldTypeRegistry.set(name, type);
    }
    const models = [
    ];
    for (const [name, model] of models) {
        env.modelManager.modelRegistry.set(name, model);
    }
}
