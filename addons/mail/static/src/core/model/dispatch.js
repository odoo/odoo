
/** @odoo-module **/

import { _store } from '@mail/core/model/_store';

import { read } from '@mail/core/structure/read';

export function dispatch(ctx, name, ...params) {
    if (!_store.models[name]) {
        throw new Error(`Cannot dispatch action "${name}" that does not exist.`);
    }
    const $action = _store.models[name];
    debugger;
    const func = read(read($action, 'Action/behavior'), 'Primitive/value');
    return func.call(null, ctx, ...params);
}
