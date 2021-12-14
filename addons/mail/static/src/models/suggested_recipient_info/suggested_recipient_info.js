/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many2one } from '@mail/model/model_field';

registerModel({
    name: 'SuggestedRecipientInfo',
    identifyingFields: ['id'],
    recordMethods: {
        /**
         * Prevents selecting a recipient that does not have a partner.
         *
         * @private
         * @returns {boolean}
         */
        _computeIsSelected() {
            return this.partner ? this.isSelected : false;
        },
        /**
         * @private
         * @returns {string}
         */
        _computeName() {
            return this.partner && this.partner.nameOrDisplayName || this.name;
        },
    },
    fields: {
        /**
         * Determines the email of `this`. It serves as visual clue when
         * displaying `this`, and also serves as default partner email when
         * creating a new partner from `this`.
         */
        email: attr({
            readonly: true,
        }),
        /**
         * States the id of this suggested recipient info. This id does not
         * correspond to any specific value, it is just a unique identifier
         * given by the creator of this record.
         */
        id: attr({
            readonly: true,
        }),
        /**
         * Determines whether `this` will be added to recipients when posting a
         * new message on `this.thread`.
         */
        isSelected: attr({
            compute: '_computeIsSelected',
            default: true,
        }),
        /**
         * Determines the lang of 'this'. Serves as default partner lang when
         * creating a new partner from 'this'.
         */
        lang: attr(),
        /**
         * Determines the name of `this`. It serves as visual clue when
         * displaying `this`, and also serves as default partner name when
         * creating a new partner from `this`.
         */
        name: attr({
            compute: '_computeName',
        }),
        /**
         * Determines the optional `Partner` associated to `this`.
         */
        partner: many2one('Partner'),
        /**
         * Determines why `this` is a suggestion for `this.thread`. It serves as
         * visual clue when displaying `this`.
         */
        reason: attr(),
        /**
         * Determines the `Thread` concerned by `this.`
         */
        thread: many2one('Thread', {
            inverse: 'suggestedRecipientInfoList',
            required: true,
        }),
    },
});
