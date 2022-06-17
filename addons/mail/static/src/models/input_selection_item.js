/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'InputSelectionItem',
    identifyingFields: ['inputSelectionPromptViewOwner', 'mediaDevice'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            this.messaging.userSetting.setAudioInputDevice(this.mediaDevice);
            this.inputSelectionPromptViewOwner.delete();
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseenter(ev) {
            this.update({ isSoftSelected: true });
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseleave(ev) {
            this.update({ isSoftSelected: false });
        },
    },
    fields: {
        inputSelectionPromptViewOwner: one('InputSelectionPromptView', {
            inverse: 'items',
            readonly: true,
            required: true,
        }),
        isSoftSelected: attr({
            default: false,
        }),
        mediaDevice: one('MediaDevice', {
            inverse: 'inputSelectionItems',
            readonly: true,
            required: true,
        }),
    },
});
