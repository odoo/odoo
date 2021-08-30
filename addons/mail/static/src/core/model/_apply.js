
/** @odoo-module **/

import { _store } from '@mail/core/model/_store';

import { remove } from '@mail/core/structure/remove';

/**
 * Insert changes & removals in the model store.
 */
export function _apply(transaction) {
    const transaction2 = {
        changes: {
            ids: { ...transaction?.changes?.ids ?? {} },
            records: { ...transaction?.changes?.records ?? {} },
        },
        removals: {
            ids: { ...transaction?.removals?.ids ?? {} },
            records: { ...transaction?.removals?.records ?? {} },
        },
    };
    _store.ids = {
        ..._store.ids,
        ...transaction2.changes.ids,
    };
    _store.records = {
        ..._store.records,
        ...transaction2.changes.records,
    };
    for (const id in transaction2.removals.ids) {
        delete _store.ids[id];
    }
    for (const $record in transaction2.removals.records) {
        delete _store.records[$record];
        remove($record);
    }
}
