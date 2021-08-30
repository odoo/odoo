/** @odoo-module **/

import { _store } from '@mail/core/structure/_store';

/**
 *
 * @param {structure.id} $node
 * @param {string} [name]
 * @returns {structure.id|any} structure.id if the read is on an object, otherwise the value of primitive.
 */
export function read($node, name) {
    const node = _store.nodes[$node];
    if (node.type === 'primitive') {
        return node.value;
    }
    if (node.type === 'object') {
        return _store.nodes[node.out[name]].out;
    }
    throw new Error(`Cannot read node "${$node}" with unsupported type "${node.type}".`);
}
