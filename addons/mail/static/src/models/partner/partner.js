odoo.define('mail/static/src/models/partner/partner.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2many, one2one } = require('mail/static/src/model/model_field_utils.js');

const utils = require('web.utils');

function factory(dependencies) {

    class Partner extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @private
         * @param {Object} data
         * @return {Object}
         */
        static convertData(data) {
            const data2 = {};
            if ('country' in data) {
                if (!data.country) {
                    data2.__mfield_country = [['unlink-all']];
                } else {
                    data2.__mfield_country = [['insert', {
                        __mfield_id: data.country[0],
                        __mfield_name: data.country[1],
                    }]];
                }
            }
            if ('display_name' in data) {
                data2.__mfield_display_name = data.display_name;
            }
            if ('email' in data) {
                data2.__mfield_email = data.email;
            }
            if ('id' in data) {
                data2.__mfield_id = data.id;
            }
            if ('im_status' in data) {
                data2.__mfield_im_status = data.im_status;
            }
            if ('name' in data) {
                data2.__mfield_name = data.name;
            }

            // relation
            if ('user_id' in data) {
                if (!data.user_id) {
                    data2.__mfield_user = [['unlink-all']];
                } else {
                    data2.__mfield_user = [
                        ['insert', {
                            __mfield_id: data.user_id[0],
                            __mfield_display_name: data.user_id[1],
                        }],
                    ];
                }
            }

            return data2;
        }

        /**
         * Search for partners matching `keyword`.
         *
         * @static
         * @param {Object} param0
         * @param {function} param0.callback
         * @param {string} param0.keyword
         * @param {integer} [param0.limit=10]
         */
        static async imSearch({ callback, keyword, limit = 10 }) {
            // prefetched partners
            let partners = [];
            const searchRegexp = new RegExp(
                _.str.escapeRegExp(utils.unaccent(keyword)),
                'i'
            );
            const currentPartner = this.env.messaging.__mfield_currentPartner();
            for (const partner of this.all(partner => partner.__mfield_active())) {
                if (partners.length < limit) {
                    if (
                        partner !== currentPartner &&
                        searchRegexp.test(partner.name)
                    ) {
                        partners.push(partner);
                    }
                }
            }
            if (!partners.length) {
                const partnersData = await this.env.services.rpc(
                    {
                        model: 'res.partner',
                        method: 'im_search',
                        args: [keyword, limit]
                    },
                    { shadow: true }
                );
                const newPartners = this.insert(partnersData.map(
                    partnerData => this.convertData(partnerData)
                ));
                partners.push(...newPartners);
            }
            callback(partners);
        }

        /**
         * @static
         */
        static async startLoopFetchImStatus() {
            await this._fetchImStatus();
            this._loopFetchImStatus();
        }

        /**
         * Checks whether this partner has a related user and links them if
         * applicable.
         */
        async checkIsUser() {
            const userIds = await this.async(() => this.env.services.rpc({
                model: 'res.users',
                method: 'search',
                args: [[['partner_id', '=', this.__mfield_id(this)]]],
                kwargs: {
                    context: { active_test: false },
                },
            }));
            this.update({
                __mfield_hasCheckedUser: true,
            });
            if (userIds.length > 0) {
                this.update({
                    __mfield_user: [['insert', {
                        __mfield_id: userIds[0],
                    }]],
                });
            }
        }

        /**
         * Gets the chat between the user of this partner and the current user.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @returns {mail.thread|undefined}
         */
        async getChat() {
            if (!this.__mfield_user(this) && !this.__mfield_hasCheckedUser(this)) {
                await this.async(() => this.checkIsUser());
            }
            // prevent chatting with non-users
            if (!this.__mfield_user(this)) {
                this.env.services['notification'].notify({
                    message: this.env._t("You can only chat with partners that have a dedicated user."),
                    type: 'info',
                });
                return;
            }
            return this.__mfield_user(this).getChat();
        }

        /**
         * Opens a chat between the user of this partner and the current user
         * and returns it.
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
         * Opens the most appropriate view that is a profile for this partner.
         */
        async openProfile() {
            return this.env.messaging.openDocument({
                id: this.__mfield_id(this),
                model: 'res.partner',
            });
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
         * @static
         * @private
         */
        static async _fetchImStatus() {
            let toFetchPartnersLocalIds = [];
            let partnerIdToLocalId = {};
            const toFetchPartners = this.all(partner => partner.__mfield_im_status(this) !== null);
            for (const partner of toFetchPartners) {
                toFetchPartnersLocalIds.push(partner.localId);
                partnerIdToLocalId[partner.__mfield_id(this)] = partner.localId;
            }
            if (!toFetchPartnersLocalIds.length) {
                return;
            }
            const dataList = await this.env.services.rpc({
                route: '/longpolling/im_status',
                params: {
                    partner_ids: toFetchPartnersLocalIds.map(partnerLocalId =>
                        this.get(partnerLocalId).__mfield_id(this)
                    ),
                },
            }, { shadow: true });
            for (const { id, im_status } of dataList) {
                this.insert({
                    __mfield_id: id,
                    __mfield_im_status: im_status,
                });
                delete partnerIdToLocalId[id];
            }
            // partners with no im_status => set null
            for (const noImStatusPartnerLocalId of Object.values(partnerIdToLocalId)) {
                const partner = this.get(noImStatusPartnerLocalId);
                if (partner) {
                    partner.update({
                        __mfield_im_status: null,
                    });
                }
            }
        }

        /**
         * @static
         * @private
         */
        static _loopFetchImStatus() {
            setTimeout(async () => {
                await this._fetchImStatus();
                this._loopFetchImStatus();
            }, 50 * 1000);
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeDisplayName() {
            return this.__mfield_display_name(this) || this.__mfield_user(this) && this.__mfield_user(this).__mfield_display_name(this);
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeNameOrDisplayName() {
            return (
                this.__mfield_name(this) ||
                this.__mfield_display_name(this)
            );
        }

    }

    Partner.fields = {
        __mfield_active: attr({
            default: true,
        }),
        __mfield_correspondentThreads: one2many('mail.thread', {
            inverse: '__mfield_correspondent',
        }),
        __mfield_country: many2one('mail.country'),
        __mfield_display_name: attr({
            compute: '_computeDisplayName',
            default: "",
            dependencies: [
                '__mfield_display_name',
                '__mfield_userDisplayName',
            ],
        }),
        __mfield_email: attr(),
        __mfield_failureNotifications: one2many('mail.notification', {
            related: '__mfield_messagesAsAuthor.__mfield_failureNotifications',
        }),
        /**
         * Whether an attempt was already made to fetch the user corresponding
         * to this partner. This prevents doing the same RPC multiple times.
         */
        __mfield_hasCheckedUser: attr({
            default: false,
        }),
        __mfield_id: attr(),
        __mfield_im_status: attr(),
        __mfield_memberThreads: many2many('mail.thread', {
            inverse: '__mfield_members',
        }),
        __mfield_messagesAsAuthor: one2many('mail.message', {
            inverse: '__mfield_author',
        }),
        __mfield_model: attr({
            default: 'res.partner',
        }),
        /**
         * Channels that are moderated by this partner.
         */
        __mfield_moderatedChannels: many2many('mail.thread', {
            inverse: '__mfield_moderators',
        }),
        __mfield_name: attr(),
        __mfield_nameOrDisplayName: attr({
            compute: '_computeNameOrDisplayName',
            dependencies: [
                '__mfield_display_name',
                '__mfield_name',
            ],
        }),
        __mfield_user: one2one('mail.user', {
            inverse: '__mfield_partner',
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_userDisplayName: attr({
            related: '__mfield_user.__mfield_display_name',
        }),
    };

    Partner.modelName = 'mail.partner';

    return Partner;
}

registerNewModel('mail.partner', factory);

});
