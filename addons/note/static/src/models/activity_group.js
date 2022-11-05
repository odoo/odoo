/** @odoo-module **/

import { attr, Patch } from '@mail/model';

Patch({
    name: 'ActivityGroup',
    fields: {
        isNote: attr({
            compute() {
                return this.irModel.model === 'note.note';
            },
        }),
    },
});
