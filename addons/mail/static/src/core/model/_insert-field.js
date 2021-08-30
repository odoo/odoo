
/** @odoo-module **/

import { _apply } from '@mail/core/model/_apply';
import { _insertModel } from '@mail/core/model/_insert-model';
import { _insertPrimitive } from '@mail/core/model/_insert-primitive';
import { _store } from '@mail/core/model/_store';

import { link } from '@mail/core/structure/link';
import { node } from '@mail/core/structure/node';
import { _id } from '@mail/core/structure/_id';

export function _insertField(ctx, data) {
    const data2 = { ...data };
    const fname = data2['Field/name'];
    const model = data2['Field/model'];
    delete data2['Model/name'];
    delete data2['Field/model'];
    const id = _id(ctx, { 'Field/name': name, 'Field/model': model });
    /**
     * 1. If field already exists, update and use it
     */
    if (_store.ids[id]) {
        const $field = _store.ids[id];
        // TODO: update the field
        return $field;
    }
    /**
     * 2. Make structurally the field
     */
    const $field = node();
    const $id = _insertPrimitive(ctx, { 'Primitive/value': id });
    link($field, $id, 'Record/id');
    // 2.1. Field/name
    const $fname = _insertPrimitive(ctx, { 'Primitive/value': fname });
    link($field, $fname, 'Field/name');
    // 2.2. Field/model
    const $model = _insertModel(ctx, { 'Model/name': model });
    link($field, $model, 'Field/model');
    // 2.3. Field/type
    const type = data2['Field/type'];
    const $type = _insertPrimitive(ctx, { 'Primitive/value': type });
    link($field, $type, 'Field/type');
    delete data2['Field/type'];
    // 2.4. Field/target
    // assumes model is already in model store
    // only handled for relational field
    if (['one', 'many'].includes(type)) {
        const target = data2['Field/target'];
        const $target = _insertModel(ctx, { 'Model/name': target });
        link($field, $target, 'Field/target');
        delete data2['Field/target'];
    }
    // TODO: handle other kinds of data
    /**
     * 3. Register the field in the store
     */
    _apply({
        changes: {
            ids: { [id]: $field },
            records: { [$field]: $field },
        },
    });
    return $field;
}
