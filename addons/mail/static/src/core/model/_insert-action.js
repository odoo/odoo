
/** @odoo-module **/

import { _apply } from '@mail/core/model/_apply';
import { _insertPrimitive } from '@mail/core/model/_insert-primitive';
import { _store } from '@mail/core/model/_store';

import { link } from '@mail/core/structure/link';
import { node } from '@mail/core/structure/node';
import { _id } from '@mail/core/structure/_id';

/**
 * Insert the primitive with provided data
 *
 * @param {model.Context} ctx 
 * @param {Object} data 
 * @returns {structure.Id}
 */
export function _insertAction(ctx, data) {
    const data2 = { ...data };
    const name = data2['Action/name'];
    delete data2['Action/name'];
    /**
     * 1. If action already exists, update and use it
     */
    const id = _id(ctx, { 'Action/name': name });
    if (_store.ids[id]) {
        const $action = _store.ids[id];
        // TODO: update the action
        return $action;
    }
    /**
     * 2. Make structurally the action
     */
    const $action = node();
    const $id = _insertPrimitive(ctx, { 'Primitive/value': id });
    link($action, $id, 'Record/id');
    const func = data2['Action/behavior'];
    delete data2['Action/behavior'];
    const $func = _insertPrimitive(ctx, { 'Primitive/value': func });
    link($action, $func, 'Action/behavior');
    // TODO: handle other kinds of data
    /**
     * 3. Register the action in store
     */
    _apply({
        changes: {
            ids: { [id]: $action },
            records: { [$action]: $action },
        },
    });
    return $action;
}
