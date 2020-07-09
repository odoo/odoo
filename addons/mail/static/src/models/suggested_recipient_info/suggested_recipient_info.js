odoo.define('mail/static/src/models/suggested_recipient_info/suggested_recipient_info.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one } = require('mail/static/src/model/model_field.js');
const mailUtils = require('mail.utils');

function factory(dependencies) {
    class SuggestedRecipientInfo extends dependencies['mail.model'] {
        init(...args) {
            super.init(...args);
        }

        static convertData(data) {
            const parsedEmail = data[1] && mailUtils.parseEmail(data[1]);
            const data2 = {
                checked: data[0] ? true : false,
                partner_id: data[0] ? data[0] : undefined,
                reason: data[2],
            };

            if (data2.partner_id) {
                data2.partner = [
                    ['insert', {
                        id: data2.partner_id,
                        name: parsedEmail[0],
                        email: parsedEmail[1],
                    }],
                ];
            } else {
                data2.name = '"' + parsedEmail[0] + '" (' + parsedEmail[1] + ')';
                data2.email = parsedEmail[1];
            }

            return data2;
        }

        // Private

        _computeId() {
            return this.partner ? this.partner.id : this.id;
        }

        _computeName() {
            return this.partner ? this.partner.name : this.name;
        }

        _computeEmail() {
            return this.partner ? this.partner.email : this.email;
        }
    }

    SuggestedRecipientInfo.fields = {
        id: attr({
            compute: '_computeId'
        }),
        /**
         * This field will hold the name when the user doesn't have a partner
         */
        name: attr({
            compute: '_computeName'
        }),
        /**
         * This field will hold the email when the user doesn't have a partner
         */
        email: attr({
            compute: "_computeEmail"
        }),
        /**
         * This field represent the checked status.
         */
        checked: attr({ default: true }),
        /**
         * Associated partner, if it exist
         */
        partner: many2one('mail.partner'),
        reason: attr(),
    };
    SuggestedRecipientInfo.modelName = 'mail.suggested_recipient_info';

    return SuggestedRecipientInfo;
}

registerNewModel('mail.suggested_recipient_info', factory);
});
