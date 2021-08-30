
/** @odoo-module **/

import { _apply } from '@mail/core/model/_apply';
import { _id } from '@mail/core/model/_id';
import { _store } from '@mail/core/model/_store';

import { link } from '@mail/core/structure/link';
import { node } from '@mail/core/structure/node';
import { primitive } from '@mail/core/structure/primitive';
import { slink } from '@mail/core/structure/slink';

export function _setup_03_Field(ctx) {
    const $field = node();
    const id = _id(ctx, { 'Model/name': 'Field' });
    // Model/name
    const mname = primitive('Field');
    link($field, mname, 'Model/name');
    // Record/models
    const $rmodels = node();
    link($field, $rmodels, 'Record/models');
    const modelId = _id(ctx, { 'Model/name': 'Model' });
    const $model = _store.ids[modelId];
    link($rmodels, $model, 'Model');
    const recordId = _id(ctx, { 'Model/name': 'Record' });
    const $record = _store.ids[recordId];
    slink($rmodels, $record, 'Record');
    // Field/name
    const $fname = node();
    link($field, $fname, 'Field/name');
    // Field/model
    const $fmodel = node();
    link($field, $fmodel, 'Field/model');
    // Field/type
    const $ftype = node();
    link($field, $ftype, 'Field/type');
    // Field/target
    const $ftarget = node();
    link($field, $ftarget, 'Field/target');
    // Field/inverse
    const $finverse = node();
    link($field, $finverse, 'Field/inverse');
    // Field/isReadonly
    const $fisReadonly = node();
    link($field, $fisReadonly, 'Field/isReadonly');
    // Field/isRequired
    const $fisRequired = node();
    link($field, $fisRequired, 'Field/isRequired');
    // Field/isCausal
    const $fisCausal = node();
    link($field, $fisCausal, 'Field/isCausal');
    // Field/compute
    const $fcompute = node();
    link($field, $fcompute, 'Field/compute');
    _apply({
        changes: {
            ids: { [id]: $field },
            records: { [$field]: $field },
        },
    });
}
