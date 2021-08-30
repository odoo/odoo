/** @odoo-module **/

import { _allocateId } from '@mail/core/structure/_allocate-id';
import { _apply } from '@mail/core/structure/_apply';

/**
 * Insert a (new primitive) node.
 *
 * @returns {structure.id}
 */
export function primitive() {
    const node = {
        /**
         * The id of the node.
         */
        id: _allocateId(),
        in: {},
        // Note: primitives should not have any out
        out: {},
        type: 'primitive',
        value: undefined,
    };
    _apply({
        changes: { [node.id]: node },
    });
    return node.id;
}
