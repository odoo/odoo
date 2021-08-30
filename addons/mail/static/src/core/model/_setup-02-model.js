/** @odoo-module **/

import { _apply } from '@mail/core/model/_apply';
import { _id } from '@mail/core/model/_id';
import { _store } from '@mail/core/model/_store';

import { link } from '@mail/core/structure/link';
import { node } from '@mail/core/structure/node';
import { primitive } from '@mail/core/structure/primitive';

export function _setup_02_Model(ctx) {
    const $model = node();
    const $mname = primitive('Model');
    link($model, $mname, 'Model/name');
    const id = _id(ctx, { 'Model/name': 'Model' });
    const $rmodels = node();
    link($model, $rmodels, 'Record/models');
    const recordId = _id(ctx, { 'Model/name': 'Record' });
    const $record = _store.ids[recordId];
    link($rmodels, $record, 'Record');
    _apply({
        changes: {
            ids: { [id]: $model },
            records: { [$model]: $model },
        },
    });
}
