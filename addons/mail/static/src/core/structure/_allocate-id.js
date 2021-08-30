/** @odoo-module **/

import { _store } from '@mail/core/structure/_store';

/**
 * Allocate a new id for the node that is being created.
 *
 * @returns {string}
 */
export function _allocateId() {
    const id = `${_store.id_out}${_store.nextId}${_store.id_in}`;
    _store.nextId++;
    return id;
}
