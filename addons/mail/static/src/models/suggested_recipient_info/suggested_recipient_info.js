/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one } from '@mail/model/model_field';

function factory(dependencies) {

    class SuggestedRecipientInfo extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // private
        //----------------------------------------------------------------------

        /**
         * Prevents selecting a recipient that does not have a partner.
         *
         * @private
         * @returns {boolean}
         */
        _computeIsSelected() {
            return this.partner ? this.isSelected : false;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeName() {
            return this.partner && this.partner.nameOrDisplayName || this.name;
        }

    }

    SuggestedRecipientInfo.fields = {
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
         * Determines the name of `this`. It serves as visual clue when
         * displaying `this`, and also serves as default partner name when
         * creating a new partner from `this`.
         */
        name: attr({
            compute: '_computeName',
        }),
        /**
         * Determines the optional `mail.partner` associated to `this`.
         */
        partner: many2one('mail.partner'),
        /**
         * Determines why `this` is a suggestion for `this.thread`. It serves as
         * visual clue when displaying `this`.
         */
        reason: attr(),
        /**
         * Determines the `mail.thread` concerned by `this.`
         */
        thread: many2one('mail.thread', {
            inverse: 'suggestedRecipientInfoList',
            required: true,
        }),
    };
    SuggestedRecipientInfo.identifyingFields = ['id'];
    SuggestedRecipientInfo.modelName = 'mail.suggested_recipient_info';

    return SuggestedRecipientInfo;
}

registerNewModel('mail.suggested_recipient_info', factory);
