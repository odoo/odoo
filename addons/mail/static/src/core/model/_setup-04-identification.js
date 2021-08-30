
/** @odoo-module **/

import { _apply } from '@mail/core/model/_apply';
import { _id } from '@mail/core/model/_id';
import { _store } from '@mail/core/model/_store';

import { link } from '@mail/core/structure/link';
import { node } from '@mail/core/structure/node';
import { primitive } from '@mail/core/structure/primitive';
import { slink } from '@mail/core/structure/slink';

export function _setup_04_Identification(ctx) {
    const $id = node();
    const id = _id(ctx, { 'Model/name': 'Identification' });
    // Model/name
    const mname = primitive('Identification');
    link($id, mname, 'Model/name');
    // Record/models
    const $rmodels = node();
    link($id, $rmodels, 'Record/models');
    const modelId = _id(ctx, { 'Model/name': 'Model' });
    const $model = _store.ids[modelId];
    link($rmodels, $model, 'Model');
    const recordId = _id(ctx, { 'Model/name': 'Record' });
    const $record = _store.ids[recordId];
    slink($rmodels, $record, 'Record');
    // Identification/records
    // - key: <structure.Id> of the record
    // - value: <structure.Id> of the record
    const $irecords = node();
    link($id, $irecords, 'Identification/records');
    // Identification/fields
    // - key: <structure.Id> of the field
    // - value: <structure.Id> of the field
    const $ifields = node();
    link($id, $ifields, 'Identification/fields');
    _apply({
        changes: {
            ids: { [id]: $id },
            records: { [$id]: $id },
        },
    });
}
