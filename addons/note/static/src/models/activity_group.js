/** @odoo-module **/

import { attr, registerPatch } from '@mail/model';

registerPatch({
    name: 'ActivityGroup',
    fields: {
        isNote: attr({
            compute() {
                return this.irModel.model === 'note.note';
            },
        }),
    },
});
