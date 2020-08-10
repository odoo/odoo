odoo.define('mail/static/src/models/user/user.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, one2one } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class User extends dependencies['mail.model'] {

        /**
         * @override
         */
        _willDelete() {
            if (this.env.messaging) {
                if (this === this.env.messaging.currentUser) {
                    this.env.messaging.update({ currentUser: [['unlink']] });
                }
            }
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @returns {string}
         */
        nameOrDisplayName() {
            const partner = this.partner;
            if (!partner) {
                return this.partnerDisplayName;
            }
            return partner.nameOrDisplayName;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

        /**
         * @override
         */
        _updateAfter(previous) {
            if (this.partnerDisplayName && this.partner) {
                this.partner.update({ display_name: this.partnerDisplayName });
            }
        }

    }

    User.fields = {
        id: attr(),
        model: attr({
            default: 'res.user',
        }),
        partner: one2one('mail.partner', {
            inverse: 'user',
        }),
        partnerDisplayName: attr(),
    };

    User.modelName = 'mail.user';

    return User;
}

registerNewModel('mail.user', factory);

});
