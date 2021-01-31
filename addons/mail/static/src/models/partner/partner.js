odoo.define('mail/static/src/models/partner/partner.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2many, one2one } = require('mail/static/src/model/model_field.js');

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
            if ('active' in data) {
                data2.active = data.active;
            }
            if ('country' in data) {
                if (!data.country) {
                    data2.country = [['unlink-all']];
                } else {
                    data2.country = [['insert', {
                        id: data.country[0],
                        name: data.country[1],
                    }]];
                }
            }
            if ('display_name' in data) {
                data2.display_name = data.display_name;
            }
            if ('email' in data) {
                data2.email = data.email;
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('im_status' in data) {
                data2.im_status = data.im_status;
            }
            if ('name' in data) {
                data2.name = data.name;
            }

            // relation
            if ('user_id' in data) {
                if (!data.user_id) {
                    data2.user = [['unlink-all']];
                } else {
                    let user = {};
                    if (Array.isArray(data.user_id)) {
                        user = {
                            id: data.user_id[0],
                            display_name: data.user_id[1],
                        };
                    } else {
                        user = {
                            id: data.user_id,
                        };
                    }
                    data2.user = [['insert', user]];
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
            const currentPartner = this.env.messaging.currentPartner;
            for (const partner of this.all(partner => partner.active)) {
                if (partners.length < limit) {
                    if (
                        partner !== currentPartner &&
                        searchRegexp.test(partner.name) &&
                        partner.user
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
                args: [[['partner_id', '=', this.id]]],
                kwargs: {
                    context: { active_test: false },
                },
            }, { shadow: true }));
            this.update({ hasCheckedUser: true });
            if (userIds.length > 0) {
                this.update({ user: [['insert', { id: userIds[0] }]] });
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
            if (!this.user && !this.hasCheckedUser) {
                await this.async(() => this.checkIsUser());
            }
            // prevent chatting with non-users
            if (!this.user) {
                this.env.services['notification'].notify({
                    message: this.env._t("You can only chat with partners that have a dedicated user."),
                    type: 'info',
                });
                return;
            }
            return this.user.getChat();
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
                id: this.id,
                model: 'res.partner',
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeAvatarUrl() {
            return `/web/image/res.partner/${this.id}/image_128`;
        }

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

        /**
         * @static
         * @private
         */
        static async _fetchImStatus() {
            const partnerIds = [];
            for (const partner of this.all()) {
                if (partner.im_status !== 'im_partner' && partner.id > 0) {
                    partnerIds.push(partner.id);
                }
            }
            if (partnerIds.length === 0) {
                return;
            }
            const dataList = await this.env.services.rpc({
                route: '/longpolling/im_status',
                params: {
                    partner_ids: partnerIds,
                },
            }, { shadow: true });
            this.insert(dataList);
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
            return this.display_name || this.user && this.user.display_name;
        }

        /**
         * @private
         * @returns {mail.messaging}
         */
        _computeMessaging() {
            return [['link', this.env.messaging]];
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeNameOrDisplayName() {
            return this.name || this.display_name;
        }

    }

    Partner.fields = {
        active: attr({
            default: true,
        }),
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
            dependencies: [
                'id',
            ],
        }),
        correspondentThreads: one2many('mail.thread', {
            inverse: 'correspondent',
        }),
        country: many2one('mail.country'),
        display_name: attr({
            compute: '_computeDisplayName',
            default: "",
            dependencies: [
                'display_name',
                'userDisplayName',
            ],
        }),
        email: attr(),
        failureNotifications: one2many('mail.notification', {
            related: 'messagesAsAuthor.failureNotifications',
        }),
        /**
         * Whether an attempt was already made to fetch the user corresponding
         * to this partner. This prevents doing the same RPC multiple times.
         */
        hasCheckedUser: attr({
            default: false,
        }),
        id: attr(),
        im_status: attr(),
        memberThreads: many2many('mail.thread', {
            inverse: 'members',
        }),
        messagesAsAuthor: one2many('mail.message', {
            inverse: 'author',
        }),
        /**
         * Serves as compute dependency.
         */
        messaging: many2one('mail.messaging', {
            compute: '_computeMessaging',
        }),
        model: attr({
            default: 'res.partner',
        }),
        /**
         * Channels that are moderated by this partner.
         */
        moderatedChannels: many2many('mail.thread', {
            inverse: 'moderators',
        }),
        name: attr(),
        nameOrDisplayName: attr({
            compute: '_computeNameOrDisplayName',
            dependencies: [
                'display_name',
                'name',
            ],
        }),
        user: one2one('mail.user', {
            inverse: 'partner',
        }),
        /**
         * Serves as compute dependency.
         */
        userDisplayName: attr({
            related: 'user.display_name',
        }),
    };

    Partner.modelName = 'mail.partner';

    return Partner;
}

registerNewModel('mail.partner', factory);

});
