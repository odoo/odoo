/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insert, link } from '@mail/model/model_field_command';
import { cleanSearchTerm } from '@mail/utils/utils';

registerModel({
    name: 'Partner',
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
                    data2.country = clear();
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
                    data2.user = clear();
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
            const suggestedPartners = await this.messaging.rpc(
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
                const cleanedAName = cleanSearchTerm(a.nameOrDisplayName || '');
                const cleanedBName = cleanSearchTerm(b.nameOrDisplayName || '');
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
            for (const partner of this.all(partner => partner.active)) {
                if (partners.length < limit) {
                    if (
                        partner.name &&
                        partner.user &&
                        cleanSearchTerm(partner.name).includes(cleanedSearchTerm)
                    ) {
                        partners.push(partner);
                    }
                }
            }
            if (!partners.length) {
                const partnersData = await this.messaging.rpc(
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
                if (
                    (partner.nameOrDisplayName && cleanSearchTerm(partner.nameOrDisplayName).includes(cleanedSearchTerm)) ||
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
    },
    recordMethods: {
        /**
         * Checks whether this partner has a related user and links them if
         * applicable.
         */
        async checkIsUser() {
            const userIds = await this.messaging.rpc({
                model: 'res.users',
                method: 'search',
                args: [[['partner_id', '=', this.id]]],
                kwargs: {
                    context: { active_test: false },
                },
            }, { shadow: true });
            if (!this.exists()) {
                return;
            }
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
                await this.checkIsUser();
                if (!this.exists()) {
                    return;
                }
            }
            // prevent chatting with non-users
            if (!this.user) {
                this.messaging.notify({
                    message: this.env._t("You can only chat with partners that have a dedicated user."),
                    type: 'info',
                });
                return;
            }
            return this.user.getChat();
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
            const chat = await this.getChat();
            if (!this.exists() || !chat) {
                return;
            }
            await chat.open(options);
            if (!this.exists()) {
                return;
            }
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
        _computeIsImStatusSet() {
            return Boolean(this.im_status && this.im_status !== 'im_partner');
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
        channelInvitationFormSelectablePartnerViews: many('ChannelInvitationFormSelectablePartnerView', {
            inverse: 'partner',
            isCausal: true,
        }),
        channelInvitationFormSelectedPartnerViews: many('ChannelInvitationFormSelectedPartnerView', {
            inverse: 'partner',
            isCausal: true,
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
        dmChatWithCurrentPartner: one('Thread', {
            inverse: 'correspondentOfDmChat',
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
            identifying: true,
        }),
        im_status: attr(),
        isImStatusSet: attr({
            compute: '_computeIsImStatusSet',
            readonly: true,
        }),
        /**
         * States whether this partner is online.
         */
        isOnline: attr({
            compute: '_computeIsOnline',
        }),
        model: attr({
            default: 'res.partner',
        }),
        name: attr(),
        nameOrDisplayName: attr({
            compute: '_computeNameOrDisplayName',
        }),
        otherMemberLongTypingInThreadTimers: many('OtherMemberLongTypingInThreadTimer', {
            inverse: 'partner',
            isCausal: true,
        }),
        persona: one('Persona', {
            default: {},
            inverse: 'partner',
            isCausal: true,
            readonly: true,
            required: true,
        }),
        suggestable: one('ComposerSuggestable', {
            default: {},
            inverse: 'partner',
            isCausal: true,
            readonly: true,
            required: true,
        }),
        user: one('User', {
            inverse: 'partner',
        }),
        volumeSetting: one('res.users.settings.volumes', {
            inverse: 'partner_id',
        }),
    },
});
