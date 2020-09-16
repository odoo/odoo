odoo.define('mail/static/src/models/user/user.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, one2one } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class User extends dependencies['mail.model'] {

        /**
         * @override
         */
        _willDelete() {
            if (this.env.messaging) {
                if (this === this.env.messaging.__mfield_currentUser(this)) {
                    this.env.messaging.update({
                        __mfield_currentUser: [['unlink']],
                    });
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
                data2.__mfield_id = data.id;
            }
            if ('partner_id' in data) {
                if (!data.partner_id) {
                    data2.__mfield_partner = [['unlink']];
                } else {
                    const partnerNameGet = data['partner_id'];
                    const partnerData = {
                        __mfield_display_name: partnerNameGet[1],
                        __mfield_id: partnerNameGet[0],
                    };
                    data2.__mfield_partner = [['insert', partnerData]];
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
                args: [ids],
                kwargs: {
                    context,
                    fields,
                },
            });
            return this.env.models['mail.user'].insert(usersData.map(userData =>
                this.env.models['mail.user'].convertData(userData)
            ));
        }

        /**
         * Fetches the partner of this user.
         */
        async fetchPartner() {
            return this.env.models['mail.user'].performRpcRead({
                ids: [this.__mfield_id(this)],
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
            if (!this.__mfield_partner(this)) {
                await this.async(() => this.fetchPartner());
            }
            if (!this.__mfield_partner(this)) {
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
                thread.__mfield_channel_type(this) === 'chat' &&
                thread.__mfield_correspondent(this) === this.__mfield_partner(this) &&
                thread.__mfield_model(this) === 'mail.channel' &&
                thread.__mfield_public(this) === 'private'
            );
            if (!chat) {
                chat = await this.async(() =>
                    this.env.models['mail.thread'].performRpcCreateChat({
                        partnerIds: [this.__mfield_partner(this).__mfield_id(this)],
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
            if (!this.__mfield_partner(this)) {
                await this.async(() => this.fetchPartner());
            }
            if (!this.__mfield_partner(this)) {
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
            return this.__mfield_partner(this).openProfile();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.__mfield_id}`;
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeDisplayName() {
            return this.__mfield_display_name(this) || this.__mfield_partner(this) && this.__mfield_partner(this).__mfield_display_name(this);
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeNameOrDisplayName() {
            return this.__mfield_partner(this) && this.__mfield_partner(this).__mfield_nameOrDisplayName(this) || this.__mfield_display_name(this);
        }
    }

    User.fields = {
        __mfield_id: attr(),
        __mfield_display_name: attr({
            compute: '_computeDisplayName',
            dependencies: [
                '__mfield_display_name',
                '__mfield_partnerDisplayName',
            ],
        }),
        __mfield_model: attr({
            default: 'res.user',
        }),
        __mfield_nameOrDisplayName: attr({
            compute: '_computeNameOrDisplayName',
            dependencies: [
                '__mfield_display_name',
                '__mfield_partnerNameOrDisplayName',
            ]
        }),
        __mfield_partner: one2one('mail.partner', {
            inverse: '__mfield_user',
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_partnerDisplayName: attr({
            related: '__mfield_partner.__mfield_display_name',
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_partnerNameOrDisplayName: attr({
            related: '__mfield_partner.__mfield_nameOrDisplayName',
        }),
    };

    User.modelName = 'mail.user';

    return User;
}

registerNewModel('mail.user', factory);

});
