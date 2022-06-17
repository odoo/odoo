/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'InputSelection',
    identifyingFields: ['callSettingsMenuOwner'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            this.update({ popoverView: this.popoverView ? clear() : insertAndReplace() });
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeLabel() {
            if (this.messaging.userSetting.audioInputDevice) {
                return this.messaging.userSetting.audioInputDevice.label;
            }
            return clear();
        },
    },
    fields: {
        callSettingsMenuOwner: one('CallSettingsMenu', {
            inverse: 'inputSelection',
            readonly: true,
            required: true,
        }),
        component: attr(),
        isOpen: attr({
            default: false,
        }),
        label: attr({
            compute: '_computeLabel',
            default: "",
        }),
        popoverView: one('PopoverView', {
            inverse: 'inputSelectionOwnerAsCallSettingsMenuMediaInput',
            isCausal: true,
        }),
    },
});
