/** @odoo-module **/

import { _apply } from '@mail/core/structure/_apply';
import { _store } from '@mail/core/structure/_store';
import { _update } from '@mail/core/structure/_update';

function _removeLink(transaction, $link) {
    const $in = _store.nodes[$link].in;
    const $out = _store.nodes[$link].out;
    transaction.removals[$link] = true;
    delete transaction.changes[$link];
    _update(transaction, $in, prev => {
        const res = {
            ...prev,
            out: { ...prev.out },
        };
        const link = _store.nodes[$link];
        delete res.out[link.name];
        return res;
    });
    _update(transaction, $out, prev => {
        const res = {
            ...prev,
            in: { ...prev.in },
        };
        delete res.in[$link];
        return res;
    });
}

/**
 * Remove the node `$node`
 *
 * @param {structure.id} $node
 */
export function remove($node) {
    const transaction = {
        changes: {},
        removals: {},
    };
    const node = _store.nodes[$node];
    for (const $in in node.in) {
        const $link = node.in[$in];
        _removeLink(transaction, $link);
    }
    for (const name in node.out) {
        const $link = node.out[name];
        _removeLink(transaction, $link);
    }
    transaction.removals[$node] = true;
    delete transaction.changes[$node];
    _apply(transaction);
}
