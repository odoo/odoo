odoo.define('mail/static/src/models/partner/partner.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2many, one2one } = require('mail/static/src/model/model_field.js');

const utils = require('web.utils');

function factory(dependencies) {

    let nextPublicId = -1;

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
                    data2.user = [
                        ['insert', {
                            id: data.user_id[0],
                            partnerDisplayName: data.user_id[1],
                        }],
                    ];
                }
            }

            return data2;
        }

        static getNextPublicId() {
            const id = nextPublicId;
            nextPublicId -= 1;
            return id;
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
                for (const data of partnersData) {
                    const partner = this.insert(data);
                    partners.push(partner);
                }
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

        async checkIsUser() {
            const userIds = await this.async(() => this.env.services.rpc({
                model: 'res.users',
                method: 'search',
                args: [[['partner_id', '=', this.id]]],
            }));
            if (userIds.length) {
                this.update({ user: [['insert', { id: userIds[0] }]] });
            }
        }

        /**
         * Opens an existing or new chat.
         */
        openChat() {
            const chat = this.correspondentThreads.find(thread => thread.channel_type === 'chat');
            if (chat) {
                chat.open();
            } else {
                this.env.models['mail.thread'].createChannel({
                    autoselect: true,
                    partnerId: this.id,
                    type: 'chat',
                });
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @static
         * @private
         */
        static async _fetchImStatus() {
            let toFetchPartnersLocalIds = [];
            let partnerIdToLocalId = {};
            const toFetchPartners = this.all(partner => partner.im_status !== null);
            for (const partner of toFetchPartners) {
                toFetchPartnersLocalIds.push(partner.localId);
                partnerIdToLocalId[partner.id] = partner.localId;
            }
            if (!toFetchPartnersLocalIds.length) {
                return;
            }
            const dataList = await this.env.services.rpc({
                route: '/longpolling/im_status',
                params: {
                    partner_ids: toFetchPartnersLocalIds.map(partnerLocalId =>
                        this.get(partnerLocalId).id
                    ),
                },
            }, { shadow: true });
            for (const { id, im_status } of dataList) {
                this.insert({ id, im_status });
                delete partnerIdToLocalId[id];
            }
            // partners with no im_status => set null
            for (const noImStatusPartnerLocalId of Object.values(partnerIdToLocalId)) {
                const partner = this.get(noImStatusPartnerLocalId);
                if (partner) {
                    partner.update({ im_status: null });
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
         * @returns {string}
         */
        _computeNameOrDisplayName() {
            return this.name || this.display_name;
        }

        /**
         * @override
         */
        _createRecordLocalId(data) {
            const Partner = this.env.models['mail.partner'];
            return `${Partner.modelName}_${data.id}`;
        }

    }

    Partner.fields = {
        active: attr({
            default: true,
        }),
        correspondentThreads: one2many('mail.thread', {
            inverse: 'correspondent',
        }),
        country: many2one('mail.country'),
        display_name: attr({
            default: "",
        }),
        email: attr(),
        failureNotifications: one2many('mail.notification', {
            related: 'messagesAsAuthor.failureNotifications',
        }),
        id: attr(),
        im_status: attr(),
        memberThreads: many2many('mail.thread', {
            inverse: 'members',
        }),
        messagesAsAuthor: one2many('mail.message', {
            inverse: 'author',
        }),
        model: attr({
            default: 'res.partner',
        }),
        moderatedChannelIds: attr({
            default: [],
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
    };

    Partner.modelName = 'mail.partner';

    return Partner;
}

registerNewModel('mail.partner', factory);

});
