/** @odoo-module **/

import { _store } from '@mail/core/structure/_store';

/**
 * Insert changes & removals in the node store.
 *
 * @param {Object} param0
 * @param {Object} param0.changes keys are ids of changes nodes and values are fully new state of corresponding changed nodes.
 * @param {Object} param0.removals keys are ids of nodes to be removed.
 */
export function _apply({ changes, removals }) {
    _store.nodes = {
        ..._store.nodes,
        ...changes,
    };
    for (const $removal in removals) {
        delete _store.nodes[$removal];
    }
}
