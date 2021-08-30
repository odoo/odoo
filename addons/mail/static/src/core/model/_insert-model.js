
/** @odoo-module **/

import { _apply } from '@mail/core/model/_apply';
import { _insertPrimitive } from '@mail/core/model/_insert-primitive';
import { _store } from '@mail/core/model/_store';

import { link } from '@mail/core/structure/link';
import { node } from '@mail/core/structure/node';
import { _id } from '@mail/core/structure/_id';

// TODO: 
/**
 * Insert the model with provided data
 *
 * @param {model.Context} ctx
 * @param {Object} data 
 * @returns {structure.Id}
 */
export function _insertModel(ctx, data) {
    const data2 = { ...data };
    const name = data2['Model/name'];
    delete data2['Model/name'];
    /**
     * 1. If model already exists, update and use it
     */
    const id = _id(ctx, { 'Model/name': name });
    if (_store.ids[id]) {
        const $model = _store.ids[id];
        return $model;
    }
    /**
     * 2. Make structurally the model
     */
    // 2.1. Core
    const $model = node();
    const $id = _insertPrimitive(ctx, { 'Primitive/value': id });
    link($model, $id, 'Record/id');
    // 2.2. Model/name
    const $name = _insertPrimitive(ctx, { 'Primitive/value': name });
    link($model, $name, 'Model/name');
    /**
     * 3. Register the model in store
     */
    _apply({
        changes: {
            ids: { [id]: $model },
            nodes: { [$model]: $model },
        },
    });
    return $model;
}
