/** @odoo-module **/

import { _store } from '@mail/core/structure/_store';

export function _update(transaction, $node, func) {
    if (!transaction.changes[$node]) {
        transaction.changes[$node] = {
            ..._store.nodes[$node]
        };
    }
    transaction.changes[$node] = {
        ...func(transaction.changes[$node])
    };
}
