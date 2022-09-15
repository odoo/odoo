/** @odoo-module **/

import { addFields } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import '@mail/models/activity_group'; // ensure the model definition is loaded before the patch

addFields('ActivityGroup', {
    isNote: attr({
        compute() {
            return this.irModel.model === 'note.note';
        },
    }),
});
