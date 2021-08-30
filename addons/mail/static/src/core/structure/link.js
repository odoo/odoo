/** @odoo-module **/

import { _allocateId } from '@mail/core/structure/_allocate-id';
import { _apply } from '@mail/core/structure/_apply';
import { _store } from '@mail/core/structure/_store';
import { _update } from '@mail/core/structure/_update';

/**
 * Link from node `$in` to node `$out` with name `name`.
 *
 * @param {structure.id} $in 
 * @param {structure.id} $out 
 * @param {string} [name]
 */
export function link($in, $out, name) {
    const _in = _store.nodes[$in];
    const out = _store.nodes[$out];
    if (!_in) {
        debugger;
    }
    if (!out) {
        debugger;
    }
    if (_in.type !== 'object') {
        throw new Error(`cannot link with '$in' being not an object (is a ${_in.type}) [ link(${$in}, ${$out}, ${name}) ]`);
    }
    if (out.type === 'link') {
        throw new Error(`cannot link with '$out' being link [ link(${$in}, ${$out}, ${name}) ]`);
    }
    const $oldOut = _in.out[name];
    if ($oldOut && _store.nodes[$oldOut].out === $out) {
        // already linked with same ref name
        return;
    }
    const transaction = {
        changes: {},
        removals: {},
    };
    const link = {
        id: _allocateId(),
        in: $in,
        name,
        out: $out,
        type: 'link',
    };
    transaction.changes[link.id] = link;
    _update(transaction, $in, prev => ({
        ...prev,
        out: {
            ...prev.out,
            [name]: link.id,
        }
    }));
    _update(transaction, $out, prev => ({
        ...prev,
        in: {
            ...prev.in,
            [link.id]: true,
        },
    }));
    if ($oldOut) {
        const $oldOutNode = _store.nodes[$oldOut].out;
        _update(transaction, $oldOutNode, prev => {
            const res = {
                ...prev,
                in: { ...prev.in },
            };
            delete res.in[$oldOutNode];
            return res;
        });
    }
    transaction.removals[$oldOut] = true;
    _apply(transaction);
}
