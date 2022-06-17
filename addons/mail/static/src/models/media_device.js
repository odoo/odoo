/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';

registerModel({
    name: 'MediaDevice',
    identifyingFields: ['id'],
    fields: {
        inputSelectionItems: many('InputSelectionItem', {
            inverse: 'mediaDevice',
            isCausal: true,
        }),
        id: attr({
            readonly: true,
            required: true,
        }),
        kind: attr(),
        label: attr(),
    },
});
