/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { insert, link, unlinkAll } from '@mail/model/model_field_command';
import { cleanSearchTerm } from '@mail/utils/utils';

registerModel({
    name: 'Partner',
    identifyingFields: ['id'],
    modelMethods: {
        /**
         * @param {Object} data
         * @return {Object}
         */
        convertData(data) {
            const data2 = {};
            if ('active' in data) {
                data2.active = data.active;
            }
            if ('country' in data) {
                if (!data.country) {
                    data2.country = unlinkAll();
                } else {
                    data2.country = insert({
                        id: data.country[0],
                        name: data.country[1],
                    });
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
                    data2.user = unlinkAll();
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
                    user.isInternalUser = data.is_internal_user;
                    data2.user = insert(user);
                }
            }

            return data2;
        },
        /**
         * Fetches partners matching the given search term to extend the
         * JS knowledge and to update the suggestion list accordingly.
         *
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {Thread} [options.thread] prioritize and/or restrict
         *  result in the context of given thread
         */
        async fetchSuggestions(searchTerm, { thread } = {}) {
            const kwargs = { search: searchTerm };
            const isNonPublicChannel = thread && thread.model === 'mail.channel' && thread.public !== 'public';
            if (isNonPublicChannel) {
                kwargs.channel_id = thread.id;
            }
            const suggestedPartners = await this.env.services.rpc(
                {
                    model: 'res.partner',
                    method: 'get_mention_suggestions',
                    kwargs,
                },
                { shadow: true },
            );
            const partners = this.messaging.models['Partner'].insert(suggestedPartners.map(data =>
                this.messaging.models['Partner'].convertData(data)
            ));
            if (isNonPublicChannel) {
                thread.update({ members: link(partners) });
            }
        },
        /**
         * Returns a sort function to determine the order of display of partners
         * in the suggestion list.
         *
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {Thread} [options.thread] prioritize result in the
         *  context of given thread
         * @returns {function}
         */
        getSuggestionSortFunction(searchTerm, { thread } = {}) {
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            return (a, b) => {
                const isAInternalUser = a.user && a.user.isInternalUser;
                const isBInternalUser = b.user && b.user.isInternalUser;
                if (isAInternalUser && !isBInternalUser) {
                    return -1;
                }
                if (!isAInternalUser && isBInternalUser) {
                    return 1;
                }
                if (thread && thread.model === 'mail.channel') {
                    const isAMember = thread.members.includes(a);
                    const isBMember = thread.members.includes(b);
                    if (isAMember && !isBMember) {
                        return -1;
                    }
                    if (!isAMember && isBMember) {
                        return 1;
                    }
                }
                if (thread) {
                    const isAFollower = thread.followersPartner.includes(a);
                    const isBFollower = thread.followersPartner.includes(b);
                    if (isAFollower && !isBFollower) {
                        return -1;
                    }
                    if (!isAFollower && isBFollower) {
                        return 1;
                    }
                }
                const cleanedAName = cleanSearchTerm(a.name || '');
                const cleanedBName = cleanSearchTerm(b.name || '');
                if (cleanedAName.startsWith(cleanedSearchTerm) && !cleanedBName.startsWith(cleanedSearchTerm)) {
                    return -1;
                }
                if (!cleanedAName.startsWith(cleanedSearchTerm) && cleanedBName.startsWith(cleanedSearchTerm)) {
                    return 1;
                }
                if (cleanedAName < cleanedBName) {
                    return -1;
                }
                if (cleanedAName > cleanedBName) {
                    return 1;
                }
                const cleanedAEmail = cleanSearchTerm(a.email || '');
                const cleanedBEmail = cleanSearchTerm(b.email || '');
                if (cleanedAEmail.startsWith(cleanedSearchTerm) && !cleanedAEmail.startsWith(cleanedSearchTerm)) {
                    return -1;
                }
                if (!cleanedBEmail.startsWith(cleanedSearchTerm) && cleanedBEmail.startsWith(cleanedSearchTerm)) {
                    return 1;
                }
                if (cleanedAEmail < cleanedBEmail) {
                    return -1;
                }
                if (cleanedAEmail > cleanedBEmail) {
                    return 1;
                }
                return a.id - b.id;
            };
        },
        /**
         * Search for partners matching `keyword`.
         *
         * @param {Object} param0
         * @param {function} param0.callback
         * @param {string} param0.keyword
         * @param {integer} [param0.limit=10]
         */
        async imSearch({ callback, keyword, limit = 10 }) {
            // prefetched partners
            let partners = [];
            const cleanedSearchTerm = cleanSearchTerm(keyword);
            const currentPartner = this.messaging.currentPartner;
            for (const partner of this.all(partner => partner.active)) {
                if (partners.length < limit) {
                    if (
                        partner !== currentPartner &&
                        partner.name &&
                        partner.user &&
                        cleanSearchTerm(partner.name).includes(cleanedSearchTerm)
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
        },
        /**
         * Returns partners that match the given search term.
         *
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {Thread} [options.thread] prioritize and/or restrict
         *  result in the context of given thread
         * @returns {[Partner[], Partner[]]}
         */
        searchSuggestions(searchTerm, { thread } = {}) {
            let partners;
            const isNonPublicChannel = thread && thread.model === 'mail.channel' && thread.public !== 'public';
            if (isNonPublicChannel) {
                // Only return the channel members when in the context of a
                // non-public channel. Indeed, the message with the mention
                // would be notified to the mentioned partner, so this prevents
                // from inadvertently leaking the private message to the
                // mentioned partner.
                partners = thread.members;
            } else {
                partners = this.messaging.models['Partner'].all();
            }
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            const mainSuggestionList = [];
            const extraSuggestionList = [];
            for (const partner of partners) {
                if (
                    (!partner.active && partner !== this.messaging.partnerRoot) ||
                    partner.id <= 0 ||
                    this.messaging.publicPartners.includes(partner)
                ) {
                    // ignore archived partners (except OdooBot), temporary
                    // partners (livechat guests), public partners (technical)
                    continue;
                }
                if (!partner.name) {
                    continue;
                }
                if (
                    (cleanSearchTerm(partner.name).includes(cleanedSearchTerm)) ||
                    (partner.email && cleanSearchTerm(partner.email).includes(cleanedSearchTerm))
                ) {
                    if (partner.user) {
                        mainSuggestionList.push(partner);
                    } else {
                        extraSuggestionList.push(partner);
                    }
                }
            }
            return [mainSuggestionList, extraSuggestionList];
        },
        async startLoopFetchImStatus() {
            await this._fetchImStatus();
            this._loopFetchImStatus();
        },
        /**
         * @private
         */
        async _fetchImStatus() {
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
        },
        /**
         * @private
         */
        _loopFetchImStatus() {
            setTimeout(async () => {
                await this._fetchImStatus();
                this._loopFetchImStatus();
            }, 50 * 1000);
        },
    },
    recordMethods: {
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
                this.update({ user: insert({ id: userIds[0] }) });
            }
        },
        /**
         * Gets the chat between the user of this partner and the current user.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @returns {Thread|undefined}
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
        },
        /**
         * Returns the text that identifies this partner in a mention.
         *
         * @returns {string}
         */
        getMentionText() {
            return this.name;
        },
        /**
         * Opens a chat between the user of this partner and the current user
         * and returns it.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @param {Object} [options] forwarded to @see `Thread:open()`
         * @returns {Thread|undefined}
         */
        async openChat(options) {
            const chat = await this.async(() => this.getChat());
            if (!chat) {
                return;
            }
            await this.async(() => chat.open(options));
            return chat;
        },
        /**
         * Opens the most appropriate view that is a profile for this partner.
         */
        async openProfile() {
            return this.messaging.openDocument({
                id: this.id,
                model: 'res.partner',
            });
        },
        /**
         * @private
         * @returns {string}
         */
        _computeAvatarUrl() {
            return `/web/image/res.partner/${this.id}/avatar_128`;
        },
        /**
         * @private
         * @returns {string|undefined}
         */
        _computeDisplayName() {
            return this.display_name || this.user && this.user.display_name;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsOnline() {
            return ['online', 'away'].includes(this.im_status);
        },
        /**
         * @private
         * @returns {string|undefined}
         */
        _computeNameOrDisplayName() {
            return this.name || this.display_name;
        },
    },
    fields: {
        active: attr({
            default: true,
        }),
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
        }),
        country: one('Country'),
        /**
         * Deprecated.
         * States the `display_name` of this partner, as returned by the server.
         * The value of this field is unreliable (notably its value depends on
         * context on which it was received) therefore it should only be used as
         * a default if the actual `name` is missing (@see `nameOrDisplayName`).
         * And if a specific name format is required, it should be computed from
         * relevant fields instead.
         */
        display_name: attr({
            compute: '_computeDisplayName',
            default: "",
        }),
        email: attr(),
        /**
         * Whether an attempt was already made to fetch the user corresponding
         * to this partner. This prevents doing the same RPC multiple times.
         */
        hasCheckedUser: attr({
            default: false,
        }),
        id: attr({
            readonly: true,
            required: true,
        }),
        im_status: attr(),
        /**
         * States whether this partner is online.
         */
        isOnline: attr({
            compute: '_computeIsOnline',
        }),
        memberThreads: many('Thread', {
            inverse: 'members',
        }),
        model: attr({
            default: 'res.partner',
        }),
        name: attr(),
        nameOrDisplayName: attr({
            compute: '_computeNameOrDisplayName',
        }),
        rtcSessions: many('RtcSession', {
            inverse: 'partner',
        }),
        user: one('User', {
            inverse: 'partner',
        }),
        volumeSetting: one('VolumeSetting', {
            inverse: 'partner',
        }),
    },
});
