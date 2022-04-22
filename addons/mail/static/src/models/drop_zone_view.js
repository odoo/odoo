/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'DropZoneView',
    identifyingFields: [['attachmentBoxViewOwner', 'composerViewOwner']],
    fields: {
        attachmentBoxViewOwner: one('AttachmentBoxView', {
            inverse: 'dropZoneView',
            readonly: true,
        }),
        composerViewOwner: one('ComposerView', {
            inverse: 'dropZoneView',
            readonly: true,
        }),
    },
});
