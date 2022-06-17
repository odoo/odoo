/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Persona',
    identifyingFields: [['guest', 'partner']],
    recordMethods: {
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeImStatus() {
            if (this.guest) {
                return this.guest.im_status || clear();
            }
            if (this.partner) {
                return this.partner.im_status || clear();
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeName() {
            if (this.guest) {
                return this.guest.name || clear();
            }
            if (this.partner) {
                return this.partner.nameOrDisplayName || clear();
            }
            return clear();
        },
    },
    fields: {
        guest: one('Guest', {
            inverse: 'persona',
            readonly: true,
        }),
        im_status: attr({
            compute: '_computeImStatus',
            readonly: true,
        }),
        name: attr({
            compute: '_computeName',
            readonly: true,
        }),
        partner: one('Partner', {
            inverse: 'persona',
            readonly: true,
        }),
    },
});
