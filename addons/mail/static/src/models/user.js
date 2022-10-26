/** @odoo-module **/

import { attr, clear, insert, many, one, Model } from '@mail/model';

Model({
    name: 'User',
    modelMethods: {
        /**
         * @param {Object} data
         * @returns {Object}
         */
        convertData(data) {
            const data2 = {};
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('partner_id' in data) {
                if (!data.partner_id) {
                    data2.partner = clear();
                } else {
                    const partnerNameGet = data['partner_id'];
                    const partnerData = {
                        display_name: partnerNameGet[1],
                        id: partnerNameGet[0],
                    };
                    data2.partner = insert(partnerData);
                }
            }
            return data2;
        },
        /**
         * Performs the `read` RPC on `res.users`.
         *
         * @param {Object} param0
         * @param {Object} param0.context
         * @param {string[]} param0.fields
         * @param {integer[]} param0.ids
         */
        async performRpcRead({ context, fields, ids }) {
            const usersData = await this.messaging.rpc({
                model: 'res.users',
                method: 'read',
                args: [ids, fields],
                kwargs: {
                    context,
                },
            }, { shadow: true });
            return this.messaging.models['User'].insert(usersData.map(userData =>
                this.messaging.models['User'].convertData(userData)
            ));
        },
    },
    recordMethods: {
        /**
         * Fetches the partner of this user.
         */
        async fetchPartner() {
            return this.messaging.models['User'].performRpcRead({
                ids: [this.id],
                fields: ['partner_id'],
                context: { active_test: false },
            });
        },
        /**
         * Opens the most appropriate view that is a profile for this user.
         * Because user is a rather technical model to allow login, it's the
         * partner profile that contains the most useful information.
         *
         * @override
         */
        async openProfile() {
            if (!this.partner) {
                await this.fetchPartner();
                if (!this.exists()) {
                    return;
                }
            }
            if (!this.partner) {
                // This user has been deleted from the server or never existed:
                // - Validity of id is not verified at insert.
                // - There is no bus notification in case of user delete from
                //   another tab or by another user.
                this.messaging.notify({
                    message: this.env._t("You can only open the profile of existing users."),
                    type: 'warning',
                });
                return;
            }
            return this.partner.openProfile();
        },
    },
    fields: {
        activitiesAsAssignee: many('Activity', { inverse: 'assignee' }),
        id: attr({ identifying: true }),
        /**
         * Determines whether this user is an internal user. An internal user is
         * a member of the group `base.group_user`. This is the inverse of the
         * `share` field in python.
         */
        isInternalUser: attr(),
        display_name: attr(),
        displayName: attr({ default: "",
            compute() {
                if (this.display_name) {
                    return this.display_name;
                }
                if (this.partner && this.partner.displayName) {
                    return this.partner.displayName;
                }
                return clear();
            },
        }),
        model: attr({ default: 'res.user' }),
        nameOrDisplayName: attr({
            compute() {
                return this.partner && this.partner.nameOrDisplayName || this.display_name;
            },
        }),
        partner: one('Partner', { inverse: 'user' }),
        res_users_settings_id: one('res.users.settings', { inverse: 'user_id' }),
    },
});
