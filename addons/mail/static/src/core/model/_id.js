/** @odoo-module **/

import { _insertPrimitive } from '@mail/core/model/_insert-primitive';
import { _store } from '@mail/core/model/_store';

/**
 * Get the model.Id given the data
 *
 * @param {model.Context} ctx
 * @param {Object} data
 * @returns {model.Id}
 */
export function _id(ctx, data) {
    /**
     * 1. Order data in utf-16 characters order of key.
     */
    const orderedKeys = [];
    for (const dname in data) {
        let isInserted = false;
        let i = 0;
        while (!isInserted && i < orderedKeys.length) {
            if (orderedKeys[i] < dname) {
                orderedKeys.splice(i - 1, 0, dname);
                isInserted = true;
            }
            i++;
        }
        if (!isInserted) {
            orderedKeys.push(dname);
        }
    }
    /**
     * 2. Process value in case it's not $node but an array, object, or primitive.
     *    Values in array/object could either be $node or primitives.
     *    No further nested array/object.
     */
    const data2 = {};
    for (const dname of orderedKeys) {
        const value = data[dname];
        if (typeof value === 'object' && value !== null) {
            const obj = {};
            if (Array.isArray(value)) {
                // Array: use value as key
                for (const itemIndex in value) {
                    const itemValue = value[itemIndex];
                    if (_store.records[itemValue]) {
                        obj[itemValue] = itemValue;
                        continue;
                    }
                    if (_store.primitives.has(itemValue)) {
                        const $primitive = _store.primitives.get(itemValue);
                        obj[$primitive] = $primitive;
                        continue;
                    }
                    // Value is an unexisting primitive: make it
                    const $primitive = _insertPrimitive(ctx, { 'Primitive/value': itemValue });
                    obj[$primitive] = $primitive;
                }
            } else {
                // Object: use provided key
                for (const itemIndex in value) {
                    const itemValue = value[itemIndex];
                    if (_store.records[itemValue]) {
                        obj[itemIndex] = itemValue;
                        continue;
                    }
                    if (_store.primitives.has(itemValue)) {
                        const $primitive = _store.primitives.get(itemValue);
                        obj[itemIndex] = $primitive;
                        continue;
                    }
                    // Value is an unexisting primitive: make it
                    const $primitive = _insertPrimitive(ctx, { 'Primitive/value': itemValue });
                    obj[itemIndex] = $primitive;
                }
            }
            data2[dname] = obj;
            continue;
        }
        if (_store.records[value]) {
            data2[dname] = value;
            continue;
        }
        if (_store.primitives.has(value)) {
            data2[dname] = _store.primitives.get(value);
            continue;
        }
        // Value is an unexisting primitive: make it
        const $primitive = _insertPrimitive(ctx, { 'Primitive/value': value });
        data2[dname] = $primitive;
    }
    /**
     * 3. Produce the model/id.
     */
    const id = `${
        _store.id_in
    }${
        orderedKeys.map(key => `${
            key
        }${
            _store.id_sep1
        }${
            (() => {
                const value = data2[key];
                if (typeof value === 'object' && value !== null) {
                    return `${
                        _store.id_sub_in
                    }${
                        value.map(vkey => `${
                            vkey
                        }${
                            _store.id_sep1
                        }${
                            value[vkey]
                        }`).join(_store.id_sep2)
                    }${
                        _store.id_sub_out
                    }`;
                }
                return value;
            })()
        }`).join(_store.id_sep2)
    }${
        _store.id_out
    }`;
    return id;
}
