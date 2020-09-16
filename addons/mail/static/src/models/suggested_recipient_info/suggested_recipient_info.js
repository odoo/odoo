odoo.define('mail/static/src/models/suggested_recipient_info/suggested_recipient_info.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one } = require('mail/static/src/model/model_field_utils.js');

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
            return (
                this.__mfield_partner(this) && this.__mfield_partner(this).__mfield_email(this) ||
                this.__mfield_email(this)
            );
        }

        /**
         * Prevents selecting a recipient that does not have a partner.
         *
         * @private
         * @returns {boolean}
         */
        _computeIsSelected() {
            return this.__mfield_partner(this) ? this.__mfield_isSelected(this) : false;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeName() {
            return (
                this.__mfield_partner(this) && this.__mfield_partner(this).__mfield_nameOrDisplayName(this) ||
                this.__mfield_name(this)
            );
        }

    }

    SuggestedRecipientInfo.fields = {
        /**
         * Determines the email of `this`. It serves as visual clue when
         * displaying `this`, and also serves as default partner email when
         * creating a new partner from `this`.
         */
        __mfield_email: attr({
            compute: '_computeEmail',
            dependencies: [
                '__mfield_email',
                '__mfield_partnerEmail',
            ],
        }),
        /**
         * Determines whether `this` will be added to recipients when posting a
         * new message on `this.thread`.
         */
        __mfield_isSelected: attr({
            compute: '_computeIsSelected',
            default: true,
            dependencies: [
                '__mfield_isSelected',
                '__mfield_partner',
            ],
        }),
        /**
         * Determines the name of `this`. It serves as visual clue when
         * displaying `this`, and also serves as default partner name when
         * creating a new partner from `this`.
         */
        __mfield_name: attr({
            compute: '_computeName',
            dependencies: [
                '__mfield_name',
                '__mfield_partnerNameOrDisplayName',
            ],
        }),
        /**
         * Determines the optional `mail.partner` associated to `this`.
         */
        __mfield_partner: many2one('mail.partner'),
        /**
         * Serves as compute dependency.
         */
        __mfield_partnerEmail: attr({
            related: '__mfield_partner.__mfield_email'
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_partnerNameOrDisplayName: attr({
            related: '__mfield_partner.__mfield_nameOrDisplayName'
        }),
        /**
         * Determines why `this` is a suggestion for `this.thread`. It serves as
         * visual clue when displaying `this`.
         */
        __mfield_reason: attr(),
        /**
         * Determines the `mail.thread` concerned by `this.`
         */
        __mfield_thread: many2one('mail.thread', {
            inverse: '__mfield_suggestedRecipientInfoList',
        }),
    };

    SuggestedRecipientInfo.modelName = 'mail.suggested_recipient_info';

    return SuggestedRecipientInfo;
}

registerNewModel('mail.suggested_recipient_info', factory);

});
