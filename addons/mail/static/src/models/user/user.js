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
         * @static
         * @param {Object} data
         * @returns {Object}
         */
        static convertData(data) {
            const data2 = {};
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('partner_id' in data) {
                if (!data.partner_id) {
                    data2.partner = [['unlink']];
                } else {
                    const partnerNameGet = data['partner_id'];
                    const partnerData = {
                        display_name: partnerNameGet[1],
                        id: partnerNameGet[0],
                    };
                    data2.partner = [['insert', partnerData]];
                }
            }
            return data2;
        }

        /**
         * Performs the `read` RPC on `res.users`.
         *
         * @static
         * @param {Object} param0
         * @param {Object} param0.context
         * @param {string[]} param0.fields
         * @param {integer[]} param0.ids
         */
        static async performRpcRead({ context, fields, ids }) {
            const usersData = await this.env.services.rpc({
                model: 'res.users',
                method: 'read',
                args: [ids, fields],
                kwargs: {
                    context,
                },
            }, { shadow: true });
            return this.env.models['mail.user'].insert(usersData.map(userData =>
                this.env.models['mail.user'].convertData(userData)
            ));
        }

        /**
         * Fetches the partner of this user.
         */
        async fetchPartner() {
            return this.env.models['mail.user'].performRpcRead({
                ids: [this.id],
                fields: ['partner_id'],
                context: { active_test: false },
            });
        }

        /**
         * Gets the chat between this user and the current user.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @returns {mail.thread|undefined}
         */
        async getChat() {
            if (!this.partner) {
                await this.async(() => this.fetchPartner());
            }
            if (!this.partner) {
                // This user has been deleted from the server or never existed:
                // - Validity of id is not verified at insert.
                // - There is no bus notification in case of user delete from
                //   another tab or by another user.
                this.env.services['notification'].notify({
                    message: this.env._t("You can only chat with existing users."),
                    type: 'warning',
                });
                return;
            }
            // in other cases a chat would be valid, find it or try to create it
            let chat = this.env.models['mail.thread'].find(thread =>
                thread.channel_type === 'chat' &&
                thread.correspondent === this.partner &&
                thread.model === 'mail.channel' &&
                thread.public === 'private'
            );
            if (!chat ||!chat.isPinned) {
                // if chat is not pinned then it has to be pinned client-side
                // and server-side, which is a side effect of following rpc
                chat = await this.async(() =>
                    this.env.models['mail.thread'].performRpcCreateChat({
                        partnerIds: [this.partner.id],
                    })
                );
            }
            if (!chat) {
                this.env.services['notification'].notify({
                    message: this.env._t("An unexpected error occurred during the creation of the chat."),
                    type: 'warning',
                });
                return;
            }
            return chat;
        }

        /**
         * Opens a chat between this user and the current user and returns it.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @param {Object} [options] forwarded to @see `mail.thread:open()`
         * @returns {mail.thread|undefined}
         */
        async openChat(options) {
            const chat = await this.async(() => this.getChat());
            if (!chat) {
                return;
            }
            await this.async(() => chat.open(options));
            return chat;
        }

        /**
         * Opens the most appropriate view that is a profile for this user.
         * Because user is a rather technical model to allow login, it's the
         * partner profile that contains the most useful information.
         *
         * @override
         */
        async openProfile() {
            if (!this.partner) {
                await this.async(() => this.fetchPartner());
            }
            if (!this.partner) {
                // This user has been deleted from the server or never existed:
                // - Validity of id is not verified at insert.
                // - There is no bus notification in case of user delete from
                //   another tab or by another user.
                this.env.services['notification'].notify({
                    message: this.env._t("You can only open the profile of existing users."),
                    type: 'warning',
                });
                return;
            }
            return this.partner.openProfile();
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
         * @private
         * @returns {string|undefined}
         */
        _computeDisplayName() {
            return this.display_name || this.partner && this.partner.display_name;
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeNameOrDisplayName() {
            return this.partner && this.partner.nameOrDisplayName || this.display_name;
        }
    }

    User.fields = {
        id: attr(),
        /**
         * Determines whether this user is an internal user. An internal user is
         * a member of the group `base.group_user`. This is the inverse of the
         * `share` field in python.
         */
        isInternalUser: attr(),
        display_name: attr({
            compute: '_computeDisplayName',
            dependencies: [
                'display_name',
                'partnerDisplayName',
            ],
        }),
        model: attr({
            default: 'res.user',
        }),
        nameOrDisplayName: attr({
            compute: '_computeNameOrDisplayName',
            dependencies: [
                'display_name',
                'partnerNameOrDisplayName',
            ]
        }),
        partner: one2one('mail.partner', {
            inverse: 'user',
        }),
        /**
         * Serves as compute dependency.
         */
        partnerDisplayName: attr({
            related: 'partner.display_name',
        }),
        /**
         * Serves as compute dependency.
         */
        partnerNameOrDisplayName: attr({
            related: 'partner.nameOrDisplayName',
        }),
    };

    User.modelName = 'mail.user';

    return User;
}

registerNewModel('mail.user', factory);

});
