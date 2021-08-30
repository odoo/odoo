
/** @odoo-module **/

import { _apply } from '@mail/core/model/_apply';
import { _store } from '@mail/core/model/_store';

import { link } from '@mail/core/structure/link';
import { node } from '@mail/core/structure/node';
import { read } from '@mail/core/structure/read';
import { _id } from '@mail/core/structure/_id';

export function _insertRecord(ctx, data) {
    /**
     * 1. If record already exists, update and use it
     */
    // FIXME: wrong: data can have several identifiers, record too
    const id = _id(ctx, data);
    if (_store.ids[id]) {
        const $record = _store.ids[id];
        // TODO: update the record
        return $record;
    }
    /**
     * 2. Make structurally the record
     */
    // 2.1. Core
    const $record = node();
    const $models = node();
    link($record, $models, 'Record/models');
    const $fields = node();
    link($record, $fields, 'Record/fields');
    const data2 = { ...data };
    // 2.2. Record/models
    if ('Record/models' in data2) {
        let modelNames;
        if (typeof data2['Record/models'] === 'string') {
            // single model
            modelNames = [data2['Record/models']];
        } else {
            // multi-models
            modelNames = data2['Record/models'];
        }
        for (const modelName of modelNames) {
            const modelId = _id(ctx, { 'Model/name': modelName });
            if (!_store.ids[modelId]) {
                throw new Error(`Failed to insert record with non-existing model "${modelName}".`);
            }
            const $model = _store.ids[modelId];
            link($models, $model, modelName);
        }
        // TODO make links from this record to model fields in models, prepare 'Record/fields'.
    }
    // 2.3. Other fields
    // TODO make links to identifier
    delete data2['Record/models'];
    for (const $data in data2) {
        if (!read($fields, $data)) {
            // throw new Error(`Failed to insert record with data "${$data}" not being a field in its models`);
        }
        // TODO insert field in record
    }
    /**
     * 3. Register the record in the store
     */
    // TODO: missing apply of identifiers
    _apply({
        changes: {
            ids: { [id]: $record },
            nodes: { [$record]: $record },
        },
    });
    return $record;
}
