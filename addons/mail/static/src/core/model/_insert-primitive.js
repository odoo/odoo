/** @odoo-module **/

import { _apply } from '@mail/core/model/_apply';
import { _store } from '@mail/core/model/_store';

import { link } from '@mail/core/structure/link';
import { node } from '@mail/core/structure/node';
import { primitive } from '@mail/core/structure/primitive';

/**
 * Insert the primitive with provided data
 *
 * @param {model.Context} ctx 
 * @param {Object} data
 * @returns {structure.Id}
 */
export function _insertPrimitive(ctx, data) {
    const value = data['Primitive/value'];
    /**
     * 1. If primitive already exists, use it
     */
    if (_store.primitives.has(value)) {
        const $primitive = _store.primitives.get(value);
        return $primitive;
    }
    /**
     * 2. Make structurally the primitive
     */
    const $primitive = node();
    const $value = primitive(value);
    link($primitive, $value, 'Primitive/value');
    const id = `${_store.id_in}Primitive/value${_store.id_sep1}${$value}${_store.id_out}`;
    /**
     * 3. Register the primitive in store
     */
    _apply({
        changes: {
            ids: { [id]: $primitive },
            records: { [$primitive]: $primitive },
        },
    });
    return $primitive;
}
