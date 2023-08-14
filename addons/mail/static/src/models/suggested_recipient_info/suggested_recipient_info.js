odoo.define('mail/static/src/models/suggested_recipient_info/suggested_recipient_info.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class SuggestedRecipientInfo extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeEmail() {
            return this.partner && this.partner.email || this.email;
        }

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
            compute: '_computeEmail',
            dependencies: [
                'email',
                'partnerEmail',
            ],
        }),
        /**
         * Determines whether `this` will be added to recipients when posting a
         * new message on `this.thread`.
         */
        isSelected: attr({
            compute: '_computeIsSelected',
            default: true,
            dependencies: [
                'isSelected',
                'partner',
            ],
        }),
        /**
         * Determines the name of `this`. It serves as visual clue when
         * displaying `this`, and also serves as default partner name when
         * creating a new partner from `this`.
         */
        name: attr({
            compute: '_computeName',
            dependencies: [
                'name',
                'partnerNameOrDisplayName',
            ],
        }),
        /**
         * Determines the optional `mail.partner` associated to `this`.
         */
        partner: many2one('mail.partner'),
        /**
         * Serves as compute dependency.
         */
        partnerEmail: attr({
            related: 'partner.email'
        }),
        /**
         * Serves as compute dependency.
         */
        partnerNameOrDisplayName: attr({
            related: 'partner.nameOrDisplayName'
        }),
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
        }),
    };

    SuggestedRecipientInfo.modelName = 'mail.suggested_recipient_info';

    return SuggestedRecipientInfo;
}

registerNewModel('mail.suggested_recipient_info', factory);

});
