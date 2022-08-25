/** @odoo-module **/

import { addFields, addRecordMethods } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import '@mail/models/activity_group'; // ensure the model definition is loaded before the patch

addRecordMethods('ActivityGroup', {
    _computeIsNote() {
        return this.irModel.model === 'note.note';
    },
});

addFields('ActivityGroup', {
    isNote: attr({
        compute: '_computeIsNote',
    }),
});
