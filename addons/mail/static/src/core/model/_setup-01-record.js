/** @odoo-module **/

import { _apply } from '@mail/core/model/_apply';
import { _id } from '@mail/core/model/_id';

import { link } from '@mail/core/structure/link';
import { node } from '@mail/core/structure/node';
import { primitive } from '@mail/core/structure/primitive';

export function _setup_01_Record(ctx) {
    const $record = node();
    const $mname = primitive('Record');
    link($record, $mname, 'Model/name');
    const id = _id(ctx, { 'Model/name': 'Record' });
    const $models = node();
    link($record, $models, 'Record/models');
    _apply({
        changes: {
            ids: { [id]: $record },
            records: { [$record]: $record },
        },
    });
}
