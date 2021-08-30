/** @odoo-module **/

import { _apply } from '@mail/core/structure/_apply';
import { _store } from '@mail/core/structure/_store';
import { _update } from '@mail/core/structure/_update';

/**
 * Remove the link of node `$in` with name `name`.
 *
 * @param {structure.id} $in
 * @param {string} name
 */
export function unlink($in, name) {
    const _in = _store.nodes[$in];
    if (_in.type !== 'object') {
        throw new Error(`cannot unlink with '$in' being non-object [ unlink(${$in}, ${name}) ]`);
    }
    const $oldOut = _in.out[name];
    if (!$oldOut) {
        // already no link
        return;
    }
    const transaction = {
        changes: {},
        removals: {},
    };
    _update(transaction, $in, prev => {
        const res = {
            ...prev,
            out: { ...prev.out },
        };
        delete res.out[name];
        return res;
    });
    _update(transaction, _store.nodes[$oldOut].out, prev => {
        const res = {
            ...prev,
            in: { ...prev.in },
        };
        delete res.in[$oldOut];
        return res;
    });
    transaction.removals[$oldOut] = true;
    _apply(transaction);
}
