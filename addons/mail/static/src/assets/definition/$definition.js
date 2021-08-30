/** @odoo-module **/

import { dispatch } from '@mail/core/model/dispatch';
import { ready } from '@mail/core/model/ready';

(async () => {
await ready;

dispatch(null, 'Record/insert', {
    'Record/type': 'Model', // just for easy 1st impl.
    'Record/models': 'Model',
    'Model/name': 'Definition',
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Identification', // just for easy 1st impl.
    'Record/models': 'Identification',
    'Identification/fields': [
        'Definition/id',
    ],
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'chunks',
    'Field/model': 'Definition',
    'Field/type': 'many',
    'Field/target': 'DefinitionChunk',
    'Field/compute'({ ctx, record }) {
        if (
            record
            .dispatch(ctx, 'Definition/rawChunks')
            .dispatch(ctx, 'isFalsy')
        ) {
            return;
        }
        const dataList = [];
        for (
            let index = 0;
            (
                index
                <
                record
                .dispatch(ctx, 'Definition/rawChunks')
                .dispatch(ctx, 'Collection/length')
            );
            index++
        ) {
            dataList.push({
                index,
                raw: (
                    record
                    .dispatch(ctx, 'Definition/rawChunks')
                    .dispatch(ctx, 'Collection/at', index)
                ),
            });
        }
        return dataList.map(
            data => dispatch(ctx, 'Record/insert', {
                'Record/models': 'DefinitionChunk',
                ...data
            }),
        );
    },
    'Field/inverse': 'DefinitionChunk/definition',
    'Field/isCausal': true,
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'id',
    'Field/model': 'Definition',
    'Field/type': 'attr',
    'Field/isReadonly': true,
    'Field/isRequired': true,
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'raw',
    'Field/model': 'Definition',
    'Field/type': 'attr',
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'rawChunks',
    'Field/model': 'Definition',
    'Field/type': 'attr',
    'Field/compute'({ ctx, record }) {
        return (
            record
            .dispatch(ctx, 'Definition/raw')
            .split('\n')
        );
    },
});

})();
