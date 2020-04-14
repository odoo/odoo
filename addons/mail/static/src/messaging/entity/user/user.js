odoo.define('mail.messaging.entity.User', function (require) {
'use strict';

const {
    fields: {
        one2many,
        one2one,
    },
    registerNewEntity,
} = require('mail.messaging.entity.core');

function UserFactory({ Entity }) {

    class User extends Entity {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @returns {string}
         */
        get nameOrDisplayName() {
            const partner = this.partner;
            if (!partner) {
                return this._displayName;
            }
            return partner.nameOrDisplayName;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _createInstanceLocalId(data) {
            return `${this.constructor.name}_${data.id}`;
        }

        /**
         * @override
         */
        _update(data) {
            const {
                displayName,
                id = this.id,
            } = data;

            Object.assign(this, {
                id,
                model: 'res.user',
            });

            if (displayName) {
                if (this.partner) {
                    this.partner.update({ display_name: displayName });
                } else {
                    this._displayName = displayName;
                }
            }
        }

    }

    User.fields = {
        activitiesAsAssignee: one2many('Activity', {
            inverse: 'assignee',
        }),
        activitiesAsCreator: one2many('Activity', {
            inverse: 'creator',
        }),
        partner: one2one('Partner', {
            inverse: 'user',
        }),
    };

    return User;
}

registerNewEntity('User', UserFactory);

});
