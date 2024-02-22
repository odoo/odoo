/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    async _performRPC(route, args) {
        if (args.model === "res.partner" && args.method === "im_search") {
            const name = args.args[0] || args.kwargs.search;
            const limit = args.args[1] || args.kwargs.limit;
            const excluded_ids = args.args[2] || args.kwargs.excluded_ids;
            return this._mockResPartnerImSearch(name, limit, excluded_ids);
        }
        if (args.model === "res.partner" && args.method === "search_for_channel_invite") {
            const search_term = args.args[0] || args.kwargs.search_term;
            const channel_id = args.args[1] || args.kwargs.channel_id;
            const limit = args.args[2] || args.kwargs.limit;
            return this._mockResPartnerSearchForChannelInvite(search_term, channel_id, limit);
        }
        if (args.model === "res.partner" && args.method === "get_mention_suggestions") {
            return this._mockResPartnerGetMentionSuggestions(args);
        }
        if (
            args.model === "res.partner" &&
            args.method === "get_mention_suggestions_from_channel"
        ) {
            return this._mockResPartnerGetMentionSuggestionsFromChannel(args);
        }
        return super._performRPC(route, args);
    },

    /**
     * Simulates `get_mention_suggestions` on `res.partner`.
     *
     * @private
     * @returns {Array[]}
     */
    _mockResPartnerGetMentionSuggestions(args) {
        const search = (args.args[0] || args.kwargs.search || "").toLowerCase();
        const limit = args.args[1] || args.kwargs.limit || 8;
        /**
         * Returns the given list of partners after filtering it according to
         * the logic of the Python method `get_mention_suggestions` for the
         * given search term. The result is truncated to the given limit and
         * formatted as expected by the original method.
         *
         * @param {Object[]} partners
         * @param {string} search
         * @param {integer} limit
         * @returns {Object[]}
         */
        const mentionSuggestionsFilter = (partners, search, limit) => {
            const matchingPartners = [
                ...this._mockResPartnerMailPartnerFormat(
                    partners
                        .filter((partner) => {
                            // no search term is considered as return all
                            if (!search) {
                                return true;
                            }
                            // otherwise name or email must match search term
                            if (partner.name && partner.name.toLowerCase().includes(search)) {
                                return true;
                            }
                            if (partner.email && partner.email.toLowerCase().includes(search)) {
                                return true;
                            }
                            return false;
                        })
                        .map((partner) => partner.id)
                ).values(),
            ];
            // reduce results to max limit
            matchingPartners.length = Math.min(matchingPartners.length, limit);
            return matchingPartners;
        };

        // add main suggestions based on users
        const partnersFromUsers = this.getRecords("res.users", [])
            .map((user) => this.getRecords("res.partner", [["id", "=", user.partner_id]])[0])
            .filter((partner) => partner);
        const mainMatchingPartners = mentionSuggestionsFilter(partnersFromUsers, search, limit);

        let extraMatchingPartners = [];
        // if not enough results add extra suggestions based on partners
        const remainingLimit = limit - mainMatchingPartners.length;
        if (mainMatchingPartners.length < limit) {
            const partners = this.getRecords("res.partner", [
                ["id", "not in", mainMatchingPartners.map((partner) => partner.id)],
            ]);
            extraMatchingPartners = mentionSuggestionsFilter(partners, search, remainingLimit);
        }
        return mainMatchingPartners.concat(extraMatchingPartners);
    },
    /**
     * Simulates `get_channel_mention_suggestions` on `res.partner`.
     *
     * @private
     * @returns {Array[]}
     */
    _mockResPartnerGetMentionSuggestionsFromChannel(args) {
        const search = (args.args[0] || args.kwargs.search || "").toLowerCase();
        const limit = args.args[1] || args.kwargs.limit || 8;
        const channel_id = args.args[2] || args.kwargs.channel_id;

        /**
         * Returns the given list of partners after filtering it according to
         * the logic of the Python method `get_mention_suggestions` for the
         * given search term. The result is truncated to the given limit and
         * formatted as expected by the original method.
         *
         * @param {Object[]} partners
         * @param {string} search
         * @param {integer} limit
         * @returns {Object[]}
         */
        const mentionSuggestionsFilter = (partners, search, limit) => {
            const matchingPartners = [
                ...this._mockResPartnerMailPartnerFormat(
                    partners
                        .filter((partner) => {
                            const [member] = this.getRecords("discuss.channel.member", [
                                ["channel_id", "=", channel_id],
                                ["partner_id", "=", partner.id],
                            ]);
                            if (!member) {
                                return false;
                            }
                            // no search term is considered as return all
                            if (!search) {
                                return true;
                            }
                            // otherwise name or email must match search term
                            if (partner.name && partner.name.toLowerCase().includes(search)) {
                                return true;
                            }
                            if (partner.email && partner.email.toLowerCase().includes(search)) {
                                return true;
                            }
                            return false;
                        })
                        .map((partner) => partner.id)
                ).values(),
            ].map((partnerFormat) => {
                const [member] = this.getRecords("discuss.channel.member", [
                    ["channel_id", "=", channel_id],
                    ["partner_id", "=", partnerFormat.id],
                ]);
                partnerFormat["channelMembers"] = [
                    [
                        "ADD",
                        this._mockDiscussChannelMember_DiscussChannelMemberFormat([member.id])[0],
                    ],
                ];
                return partnerFormat;
            });
            // reduce results to max limit
            matchingPartners.length = Math.min(matchingPartners.length, limit);
            return matchingPartners;
        };

        // add main suggestions based on users
        const partnersFromUsers = this.getRecords("res.users", [])
            .map((user) => this.getRecords("res.partner", [["id", "=", user.partner_id]])[0])
            .filter((partner) => partner);
        const mainMatchingPartners = mentionSuggestionsFilter(partnersFromUsers, search, limit);

        let extraMatchingPartners = [];
        // if not enough results add extra suggestions based on partners
        const remainingLimit = limit - mainMatchingPartners.length;
        if (mainMatchingPartners.length < limit) {
            const partners = this.getRecords("res.partner", [
                ["id", "not in", mainMatchingPartners.map((partner) => partner.id)],
            ]);
            extraMatchingPartners = mentionSuggestionsFilter(partners, search, remainingLimit);
        }
        return mainMatchingPartners.concat(extraMatchingPartners);
    },
    /**
     * Simulates `_get_needaction_count` on `res.partner`.
     *
     * @private
     * @param {integer} id
     * @returns {integer}
     */
    _mockResPartner_GetNeedactionCount(id) {
        const partner = this.getRecords("res.partner", [["id", "=", id]])[0];
        return this.getRecords("mail.notification", [
            ["res_partner_id", "=", partner.id],
            ["is_read", "=", false],
        ]).length;
    },
    /**
     * Simulates `im_search` on `res.partner`.
     *
     * @private
     * @param {string} [name='']
     * @param {integer} [limit=20]
     * @returns {Object[]}
     */
    _mockResPartnerImSearch(name = "", limit = 20, excluded_ids = []) {
        name = name.toLowerCase(); // simulates ILIKE
        // simulates domain with relational parts (not supported by mock server)
        const matchingPartners = this.getRecords("res.users", [])
            .filter((user) => {
                const partner = this.getRecords("res.partner", [["id", "=", user.partner_id]])[0];
                // user must have a partner
                if (!partner) {
                    return false;
                }
                // not current partner
                if (partner.id === this.pyEnv.currentPartnerId) {
                    return false;
                }
                // no name is considered as return all
                if (!name) {
                    return true;
                }
                if (partner.name && partner.name.toLowerCase().includes(name)) {
                    return true;
                }
                return false;
            })
            .map((user) => {
                const partner = this.getRecords("res.partner", [["id", "=", user.partner_id]])[0];
                return {
                    id: partner.id,
                    name: partner.name,
                };
            })
            .sort((a, b) => (a.name === b.name ? a.id - b.id : a.name > b.name ? 1 : -1));
        matchingPartners.length = Math.min(matchingPartners.length, limit);
        const resultPartners = matchingPartners.filter(
            (partner) => !excluded_ids.includes(partner.id)
        );
        return [
            ...this._mockResPartnerMailPartnerFormat(
                resultPartners.map((partner) => partner.id)
            ).values(),
        ];
    },
    /**
     * Simulates `mail_partner_format` on `res.partner`.
     *
     * @private
     * @returns {integer[]} ids
     * @returns {Map}
     */
    _mockResPartnerMailPartnerFormat(ids) {
        const partners = this.getRecords("res.partner", [["id", "in", ids]], {
            active_test: false,
        });
        // Servers is also returning `is_internal_user` but not
        // done here for simplification.
        return new Map(
            partners.map((partner) => {
                const users = this.getRecords("res.users", [["id", "in", partner.user_ids]]);
                const internalUsers = users.filter((user) => !user.share);
                let mainUser;
                if (internalUsers.length > 0) {
                    mainUser = internalUsers[0];
                } else if (users.length > 0) {
                    mainUser = users[0];
                }
                return [
                    partner.id,
                    {
                        active: partner.active,
                        email: partner.email,
                        id: partner.id,
                        im_status: partner.im_status,
                        is_company: partner.is_company,
                        name: partner.name,
                        type: "partner",
                        user: mainUser
                            ? {
                                  id: mainUser.id,
                                  isInternalUser: !mainUser.share,
                              }
                            : false,
                    },
                ];
            })
        );
    },
    /**
     * Simulates `search_for_channel_invite` on `res.partner`.
     *
     * @private
     * @param {string} [search_term='']
     * @param {integer} [channel_id]
     * @param {integer} [limit=30]
     * @returns {Object[]}
     */
    _mockResPartnerSearchForChannelInvite(search_term, channel_id, limit = 30) {
        if (search_term) {
            search_term = search_term.toLowerCase(); // simulates ILIKE
        }
        const memberPartnerIds = new Set(
            this.getRecords("discuss.channel.member", [["channel_id", "=", channel_id]]).map(
                (member) => member.partner_id
            )
        );
        // simulates domain with relational parts (not supported by mock server)
        const matchingPartners = [
            ...this._mockResPartnerMailPartnerFormat(
                this.getRecords("res.users", [])
                    .filter((user) => {
                        const partner = this.getRecords("res.partner", [
                            ["id", "=", user.partner_id],
                        ])[0];
                        // user must have a partner
                        if (!partner) {
                            return false;
                        }
                        // user should not already be a member of the channel
                        if (memberPartnerIds.has(partner.id)) {
                            return false;
                        }
                        // no name is considered as return all
                        if (!search_term) {
                            return true;
                        }
                        if (partner.name && partner.name.toLowerCase().includes(search_term)) {
                            return true;
                        }
                        return false;
                    })
                    .map((user) => user.partner_id)
            ).values(),
        ];
        const count = matchingPartners.length;
        matchingPartners.length = Math.min(count, limit);
        return {
            count,
            partners: matchingPartners,
        };
    },
    /**
     * Simulates `_message_fetch_failed` on `res.partner`.
     *
     * @private
     * @param {integer} id
     * @returns {Object[]}
     */
    _mockResPartner_MessageFetchFailed(id) {
        const partner = this.getRecords("res.partner", [["id", "=", id]], {
            active_test: false,
        })[0];
        const messages = this.getRecords("mail.message", [
            ["author_id", "=", partner.id],
            ["res_id", "!=", 0],
            ["model", "!=", false],
            ["message_type", "!=", "user_notification"],
        ]).filter((message) => {
            // Purpose is to simulate the following domain on mail.message:
            // ['notification_ids.notification_status', 'in', ['bounce', 'exception']],
            // But it's not supported by getRecords domain to follow a relation.
            const notifications = this.getRecords("mail.notification", [
                ["mail_message_id", "=", message.id],
                ["notification_status", "in", ["bounce", "exception"]],
            ]);
            return notifications.length > 0;
        });
        return this._mockMailMessage_MessageNotificationFormat(
            messages.map((message) => message.id)
        );
    },
    /**
     * Simulates `_get_channels_as_member` on `res.partner`.
     *
     * @private
     * @param {integer[]} ids
     * @returns {Object}
     */
    _mockResPartner_GetChannelsAsMember(ids) {
        const partner = this.getRecords("res.partner", [["id", "in", ids]])[0];
        const channelMembers = this.getRecords("discuss.channel.member", [
            ["partner_id", "=", partner.id],
        ]);
        const channels = this.getRecords("discuss.channel", [
            ["channel_type", "in", ["channel", "group"]],
            ["channel_member_ids", "in", channelMembers.map((member) => member.id)],
        ]);
        const directMessagesMembers = this.getRecords("discuss.channel.member", [
            ["partner_id", "=", partner.id],
            ["is_pinned", "=", true],
        ]);
        const directMessages = this.getRecords("discuss.channel", [
            ["channel_type", "=", "chat"],
            ["channel_member_ids", "in", directMessagesMembers.map((member) => member.id)],
        ]);
        return [...channels, ...directMessages];
    },
    /**
     * Simulates `_get_current_persona` on `res.partner`.
     *
     */
    _mockResPartner__getCurrentPersona() {
        if (this.pyEnv.currentUser?._is_public()) {
            return [null, this._mockMailGuest__getGuestFromContext()];
        }
        return [this.pyEnv.currentPartner, null];
    },
});
