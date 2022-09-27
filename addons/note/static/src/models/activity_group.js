/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

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
