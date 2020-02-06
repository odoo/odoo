odoo.define('mail.messaging.entity.User', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

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
            return `${this.constructor.localId}_${data.id}`;
        }

        /**
         * @override
         */
        _update(data) {
            const {
                displayName,
                id = this.id,
            } = data;

            this._write({
                id,
                model: 'res.user',
            });

            if (displayName) {
                if (this.partner) {
                    this.partner.update({ display_name: displayName });
                } else {
                    this._write({ _displayName: displayName });
                }
            }
        }

    }

    Object.assign(User, {
        relations: Object.assign({}, Entity.relations, {
            activitiesAsAssignee: {
                inverse: 'assignee',
                to: 'Activity',
                type: 'one2many',
            },
            activitiesAsCreator: {
                inverse: 'creator',
                to: 'Activity',
                type: 'one2many',
            },
            partner: {
                inverse: 'user',
                to: 'Partner',
                type: 'one2one',
            },
        }),
    });

    return User;
}

registerNewEntity('User', UserFactory);

});
