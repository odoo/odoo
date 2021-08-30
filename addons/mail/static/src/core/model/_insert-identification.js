/** @odoo-module **/

import { _apply } from '@mail/core/model/_apply';
import { _insertPrimitive } from '@mail/core/model/_insertPrimitive';
import { _store } from '@mail/core/model/_store';

import { link } from '@mail/core/structure/link';
import { node } from '@mail/core/structure/node';
import { primitive } from '@mail/core/structure/primitive';
import { _id } from '@mail/core/structure/_id';

export function _insertIdentification(ctx, data) {
    // TODO make a identification record without `_insertRecord`.
    /**
     * 1. Remove data that are not Identification/fields
     */
    const data2 = { ...data };
    delete data['Record/type'];
    delete data['Record/models'];
    /**
     * 2. If identification already exists, update and use it
     */
    const id = _id(ctx, data);
    if (_store.ids[id]) {
        const $identification = _store.ids[id];
        // TODO: update the identification
        return $identification;
    }
    /**
     * 3. Make structurally the identification
     */
    const $identification = node();
    const $id = _insertPrimitive(ctx, { 'Primitive/value': id });
    link($identification, $id, 'Record/id');
    const $fields = node();
    link($identification, $fields, 'Identification/fields');
    for (const field in data2) {
        const $primitive = primitive();
        link($fields, $primitive, field);
    }
    /**
     * 4. Register the identification in the store
     */
    _apply({
        changes: {
            ids: { [id]: $identification },
            records: { [$identification]: $identification },
        },
    });
    return $identification;
}
