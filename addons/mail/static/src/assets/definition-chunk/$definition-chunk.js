/** @odoo-module **/

import { dispatch } from '@mail/core/model/dispatch';
import { ready } from '@mail/core/model/ready';

(async () => {
await ready;

dispatch(null, 'Record/insert', {
    'Record/type': 'Model', // just for easy 1st impl.
    'Record/models': 'Model',
    'Model/name': 'DefinitionChunk',
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Identification', // just for easy 1st impl.
    'Record/models': 'Identification',
    'Identification/fields': [
        'DefinitionChunk/definition',
        'DefinitionChunk/index',
    ],
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'calledAction',
    'Field/model': 'DefinitionChunk',
    'Field/type': 'one',
    'Field/target': 'Action',
    'Field/compute'({ ctx, record }) {
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/relevantPart2')
            .dispatch(ctx, 'isFalsy')
        ) {
            return dispatch(ctx, 'Record/empty');
        }
        if (
            !['call 1', 'call 2'].includes(
                record
                .dispatch(ctx, 'DefinitionChunk/type')
            )
        ) {
            return dispatch('Record/empty');
        }
        return dispatch('Record/insert', {
            'Record/models': 'Action',
            'Action/name': (
                record
                .dispatch(ctx, 'DefinitionChunk/relevantPart2')
            ),
        });
    },
    'Field/inverse': 'Action/calledDefinitionChunks',
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'definition',
    'Field/model': 'DefinitionChunk',
    'Field/type': 'one',
    'Field/target': 'Definition',
    'Field/inverse': 'Definition/chunks',
    'Field/isReadonly': 'true',
    'Field/isRequired': true,
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'elementOf',
    'Field/model': 'DefinitionChunk',
    'Field/type': 'one',
    'Field/target': 'DefinitionChunk',
    'Field/compute'({ ctx, record }) {
        let elementOf = undefined;
        let prev = (
            record
            .dispatch(ctx, 'DefinitionChunk/structuralPrevious')
        );
        while (prev && !elementOf) {
            if (
                prev
                .dispatch(ctx, 'DefinitionChunk/level')
                <
                record
                .dispatch(ctx, 'DefinitionChunk/level')
            ) {
                elementOf = prev;
            }
            prev = (
                prev
                .dispatch(ctx, 'DefinitionChunk/structuralPrevious')
            );
        }
        if (!elementOf) {
            return dispatch(ctx, 'Record/empty');
        }
        return elementOf;
    },
    'Field/inverse': 'DefinitionChunk/elements',
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'elements',
    'Field/model': 'DefinitionChunk',
    'Field/type': 'many',
    'Field/target': 'DefinitionChunk',
    'Field/inverse': 'DefinitionChunk/elementOf',
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'index',
    'Field/model': 'DefinitionChunk',
    'Field/type': 'attr',
    'Field/isReadonly': true,
    'Field/isRequired': true,
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'level',
    'Field/model': 'DefinitionChunk',
    'Field/type': 'attr',
    'Field/compute'({ ctx, record }) {
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/raw')
            .dispatch(ctx, 'isFalsy')
        ) {
            return 0;
        }
        let i = 0;
        while (
            i
            <
            record
            .dispatch(ctx, 'DefinitionChunk/raw')
            .length
            &&
            record
            .dispatch(ctx, 'DefinitionChunk/raw')
            .charCodeAt(i) === 32
        ) {
            i++;
        }
        return i;
    },
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'raw',
    'Field/model': 'DefinitionChunk',
    'Field/type': 'attr',
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'semanticalNext',
    'Field/model': 'DefinitionChunk',
    'Field/type': 'one',
    'Field/target': 'DefinitionChunk',
    'Field/compute'({ ctx, record }) {
        let next = undefined;
        let n = (
            record
            .dispatch(ctx, 'DefinitionChunk/structuralNext')
        );
        while (n && !next) {
            if (
                n
                .dispatch(ctx, 'DefinitionChunk/level')
                ===
                record
                .dispatch(ctx, 'DefinitionChunk/level')
            ) {
                next = n;
            }
            if (
                n
                .dispatch(ctx, 'DefinitionChunk/level')
                <
                record
                .dispatch(ctx, 'DefinitionChunk/level')
            ) {
                break;
            }
            n = (
                n
                .dispatch(ctx, 'DefinitionChunk/structuralNext')
            );
        }
        if (!next) {
            return dispatch(ctx, 'Record/empty');
        }
        return next;
    },
    'Field/inverse': 'DefinitionChunk/semanticalPrevious',
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'semanticalPrevious',
    'Field/model': 'DefinitionChunk',
    'Field/type': 'one',
    'Field/target': 'DefinitionChunk',
    'Field/compute'({ ctx, record }) {
        let previous = undefined;
        let p = (
            record
            .dispatch(ctx, 'DefinitionChunk/structuralPrevious')
        );
        while (p && !previous) {
            if (
                p
                .dispatch(ctx, 'DefinitionChunk/level')
                ===
                record
                .dispatch(ctx, 'DefinitionChunk/level')
            ) {
                previous = p;
            }
            if (
                p
                .dispatch(ctx, 'DefinitionChunk/level')
                <
                record
                .dispatch(ctx, 'DefinitionChunk/level')
            ) {
                break;
            }
            p = (
                p
                .dispatch(ctx, 'DefinitionChunk/structuralPrevious')
            );
        }
        if (!previous) {
            return dispatch(ctx, 'Record/empty');
        }
        return previous;
    },
    'Field/inverse': 'DefinitionChunk/semanticalNext',
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'structuralNext',
    'Field/model': 'DefinitionChunk',
    'Field/type': 'one',
    'Field/target': 'DefinitionChunk',
    'Field/compute'({ ctx, record }) {
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/definition')
            .dispatch(ctx, 'isFalsy')
        ) {
            return dispatch(ctx, 'Record/empty');
        }
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/index')
            ===
            record
            .dispatch(ctx, 'DefinitionChunk/definition')
            .dispatch(ctx, 'Definition/chunks')
            .dispatch(ctx, 'Collection/length')
            - 1
        ) {
            return dispatch(ctx, 'Record/empty');
        }
        const next = dispatch(ctx, 'Record/findById', {
            'DefinitionChunk/definition': (
                record
                .dispatch(ctx, 'DefinitionChunk/definition')
            ),
            'DefinitionChunk/index': (
                record
                .dispatch(ctx, 'DefinitionChunk/index') + 1
            ),
        });
        return next;
    },
    'Field/inverse': 'DefinitionChunk/structuralPrevious',
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'structuralPrevious',
    'Field/model': 'DefinitionChunk',
    'Field/type': 'one',
    'Field/target': 'DefinitionChunk',
    'Field/compute'({ ctx, record }) {
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/definition')
            .dispatch(ctx, 'isFalsy')
        ) {
            return dispatch(ctx, 'Record/empty');
        }
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/index')
            === 0
        ) {
            return dispatch(ctx, 'Record/empty');
        }
        const previous = dispatch(ctx, 'Record/findById', {
            'DefinitionChunk/definition': (
                record
                .dispatch(ctx, 'DefinitionChunk/definition')
            ),
            'Definition/index': (
                record
                .dispatch(ctx, 'DefinitionChunk/index')
                - 1
            ),
        });
        return previous;
    },
    'Field/inverse': 'DefinitionChunk/structuralNext',
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'relevantPart',
    'Field/model': 'DefinitionChunk',
    'Field/type': 'attr',
    'Field/compute'({ ctx, record }) {
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/raw')
            .dispatch(ctx, 'isFalsy')
        ) {
            return dispatch(ctx, 'Record/empty');
        }
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/level')
            .dispatch(ctx, 'isFalsy')
        ) {
            return dispatch(ctx, 'Record/empty');
        }
        return (
            record
            .dispatch(ctx, 'DefinitionChunk/raw')
            .substring(
                record
                .dispatch(ctx, 'Definition/level')
            )
        );
    },
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'relevantPart2',
    'Field/model': 'DefinitionChunk',
    'Field/type': 'attr',
    'Field/compute'({ ctx, record }) {
        switch (
            record
            .dispatch(ctx, 'DefinitionChunk/type')
        ) {
            case 'call 1': {
                return (
                    record
                    .dispatch(ctx, 'DefinitionChunk/relevantPart')
                    .substring(
                        1,
                        (
                            record
                            .dispatch(ctx, 'DefinitionChunk/relevantPart')
                            .length - 1
                        ),
                    )
                );
            }
            case 'call 2': {
                return (
                    record
                    .dispatch(ctx, 'DefinitionChunk/relevantPart')
                    .substring(
                        2,
                        (
                            record
                            .dispatch(ctx, 'DefinitionChunk/relevantPart')
                            .length - 1
                        ),
                    )
                );
            }
            case 'entry': {
                return (
                    record
                    .dispatch(ctx, 'DefinitionChunk/relevantPart')
                    .substring(
                        1,
                        (
                            record
                            .dispatch(ctx, 'DefinitionChunk/relevantPart')
                            .length - 1
                        ),
                    )
                );
            }
            case 'set': {
                return (
                    record
                    .dispatch(ctx, 'DefinitionChunk/relevantPart')
                    .substring(
                        1,
                        (
                            record
                            .dispatch(ctx, 'DefinitionChunk/relevantPart')
                            .length
                        ),
                    )
                );
            }
            case 'read': {
                return (
                    record
                    .dispatch(ctx, 'DefinitionChunk/relevantPart')
                    .substring(
                        1,
                        (
                            record
                            .dispatch(ctx, 'DefinitionChunk/relevantPart')
                            .length
                        ),
                    )
                );
            }
            case 'text': {
                return (
                    record
                    .dispatch(ctx, 'DefinitionChunk/relevantPart')
                );
            }
        }
    },
});
dispatch(null, 'Record/insert', {
    'Record/type': 'Field', // just for easy 1st impl.
    'Record/models': 'Field',
    'Field/name': 'type',
    'Field/model': 'DefinitionChunk',
    'Field/type': 'attr',
    'Field/compute'({ ctx, record }) {
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/relevantPart')
            .dispatch(ctx, 'isFalsy')
        ) {
            return dispatch(ctx, 'Record/empty');
        }
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/relevantPart')[0]
            ===
            '{'
            &&
            record
            .dispatch(ctx, 'DefinitionChunk/relevantPart')[
                record
                .dispatch(ctx, 'DefinitionChunk/relevantPart')
                .length - 1
            ]
            ===
            '}'
        ) {
            return 'call 1';
        }
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/relevantPart')[0]
            ===
            '.'
            &&
            record
            .dispatch(ctx, 'DefinitionChunk/relevantPart')[1]
            ===
            '{'
            &&
            record
            .dispatch(ctx, 'DefinitionChunk/relevantPart')[
                record
                .dispatch(ctx, 'DefinitionChunk/relevantPart')
                .length - 1
            ]
            ===
            '}'
        ) {
            return 'call 2';
        }
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/relevantPart')[0]
            ===
            '['
            &&
            record
            .dispatch(ctx, 'DefinitionChunk/relevantPart')[
                record
                .dispatch(ctx, 'DefinitionChunk/relevantPart')
                .length - 1
            ]
            ===
            ']'
        ) {
            return 'entry';
        }
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/relevantPart')[0]
            === ':'
        ) {
            return 'set';
        }
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/relevantPart')[0]
            === '@'
        ) {
            return 'read';
        }
        if (
            record
            .dispatch(ctx, 'DefinitionChunk/relevantPart')
            .length > 0
        ) {
            return 'text';
        }
        return 'ignore';
    },
});

})();
