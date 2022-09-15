/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insert } from '@mail/model/model_field_command';
import { cleanSearchTerm } from '@mail/utils/utils';

registerModel({
    name: 'Partner',
    modelMethods: {
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
            const isNonPublicChannel = thread && thread.model === 'mail.channel' && (thread.authorizedGroupFullName || thread.channel.channel_type !== 'channel');
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
            this.messaging.models['Partner'].insert(suggestedPartners);
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
                if (thread && thread.channel) {
                    const isAMember = a.persona.channelMembers.includes(thread.channel);
                    const isBMember = b.persona.channelMembers.includes(thread.channel);
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
                const newPartners = this.insert(partnersData);
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
            const isNonPublicChannel = thread && thread.channel && (thread.authorizedGroupFullName || thread.channel.channel_type !== 'channel');
            if (isNonPublicChannel) {
                // Only return the channel members when in the context of a
                // group restricted channel. Indeed, the message with the mention
                // would be notified to the mentioned partner, so this prevents
                // from inadvertently leaking the private message to the
                // mentioned partner.
                partners = thread.channel.channelMembers.filter(member => member.persona && member.persona.partner).map(member => member.persona.partner);
            } else {
                partners = this.messaging.models['Partner'].all();
            }
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            const mainSuggestionList = [];
            const extraSuggestionList = [];
            for (const partner of partners) {
                if (
                    (!partner.active && partner !== this.messaging.partnerRoot) ||
                    partner.is_public
                ) {
                    // ignore archived partners (except OdooBot), public partners (technical)
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
         * @returns {Channel|undefined}
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
         */
        async openChat(options) {
            const chat = await this.getChat();
            if (!this.exists() || !chat) {
                return;
            }
            await chat.thread.open(options);
            if (!this.exists()) {
                return;
            }
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
    },
    fields: {
        active: attr({
            default: true,
        }),
        avatarUrl: attr({
            compute() {
                return `/web/image/res.partner/${this.id}/avatar_128`;
            },
        }),
        channelInvitationFormSelectablePartnerViews: many('ChannelInvitationFormSelectablePartnerView', {
            inverse: 'partner',
        }),
        channelInvitationFormSelectedPartnerViews: many('ChannelInvitationFormSelectedPartnerView', {
            inverse: 'partner',
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
        display_name: attr(),
        displayName: attr({
            compute() {
                if (this.display_name) {
                    return this.display_name;
                }
                if (this.user && this.user.displayName) {
                    return this.user.displayName;
                }
                return clear();
            },
            default: "",
        }),
        dmChatWithCurrentPartner: one('Channel', {
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
            compute() {
                return Boolean(this.im_status && this.im_status !== 'im_partner');
            },
        }),
        /**
         * States whether this partner is online.
         */
        isOnline: attr({
            compute() {
                return ['online', 'away'].includes(this.im_status);
            },
        }),
        is_public: attr(),
        model: attr({
            default: 'res.partner',
        }),
        name: attr(),
        nameOrDisplayName: attr({
            compute() {
                return this.name || this.displayName;
            },
        }),
        persona: one('Persona', {
            default: {},
            inverse: 'partner',
            readonly: true,
            required: true,
        }),
        suggestable: one('ComposerSuggestable', {
            default: {},
            inverse: 'partner',
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
