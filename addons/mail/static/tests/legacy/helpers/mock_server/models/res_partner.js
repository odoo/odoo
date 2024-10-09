/** @odoo-module alias=@mail/../tests/helpers/mock_server/models/res_partner default=false */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    async _performRPC(route, args) {
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
                        userId: mainUser ? mainUser.id : false,
                        isInternalUser: mainUser ? !mainUser.share : false,
                        write_date: partner.write_date,
                    },
                ];
            })
        );
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
