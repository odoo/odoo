/** @odoo-module **/

import { _allocateId } from '@mail/core/structure/_allocate-id';
import { _apply } from '@mail/core/structure/_apply';

/**
 * Insert a (new object) node.
 *
 * @returns {structure.id}
 */
export function node() {
    const node = {
        /**
         * The id of the node.
         */
        id: _allocateId(),
        in: {},
        out: {},
        type: 'object',
    };
    _apply({
        changes: { [node.id]: node },
    });
    return node.id;
}
