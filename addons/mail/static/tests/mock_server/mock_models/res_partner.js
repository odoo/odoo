/** @odoo-module */

import { webModels } from "@web/../tests/web_test_helpers";

/**
 * @typedef {import("@web/../tests/web_test_helpers").ModelRecord} ModelRecord
 */

/**
 * @template T
 * @typedef {import("@web/../tests/web_test_helpers").KwArgs<T>} KwArgs
 */

export class ResPartner extends webModels.ResPartner {
    /**
     * Simulates `get_mention_suggestions` on `res.partner`.
     *
     * @param {string} [search]
     * @param {number} [limit]
     * @param {KwArgs<{ limit: number; search: string }>} [kwargs]
     * @returns {ModelRecord[]}
     */
    get_mention_suggestions(search, limit, kwargs = {}) {
        search = (kwargs.search || search || "").toLowerCase();
        limit = kwargs.limit || limit || 8;
        /**
         * Returns the given list of partners after filtering it according to
         * the logic of the Python method `get_mention_suggestions` for the
         * given search term. The result is truncated to the given limit and
         * formatted as expected by the original method.
         *
         * @param {ModelRecord[]} partners
         * @param {string} search
         * @param {number} limit
         */
        const mentionSuggestionsFilter = (partners, search, limit) => {
            const matchingPartners = Object.values(
                this.mail_partner_format(
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
                )
            );
            // reduce results to max limit
            matchingPartners.length = Math.min(matchingPartners.length, limit);
            return matchingPartners;
        };

        // add main suggestions based on users
        const partnersFromUsers = this.env["res.users"]
            ._filter([])
            .map((user) => this._filter([["id", "=", user.partner_id]])[0])
            .filter((partner) => partner);
        const mainMatchingPartners = mentionSuggestionsFilter(partnersFromUsers, search, limit);

        let extraMatchingPartners = [];
        // if not enough results add extra suggestions based on partners
        const remainingLimit = limit - mainMatchingPartners.length;
        if (mainMatchingPartners.length < limit) {
            const partners = this._filter([
                ["id", "not in", mainMatchingPartners.map((partner) => partner.id)],
            ]);
            extraMatchingPartners = mentionSuggestionsFilter(partners, search, remainingLimit);
        }
        return mainMatchingPartners.concat(extraMatchingPartners);
    }

    /**
     * Simulates `get_channel_mention_suggestions` on `res.partner`.
     *
     * @param {string} [search]
     * @param {number} [limit]
     * @param {number} [channelId]
     * @param {KwArgs<{ channel_id: number; limit: number; search: string }>} [kwargs]
     * @returns {ModelRecord[]}
     */
    get_channel_mention_suggestions(search, limit, channelId, kwargs = {}) {
        search = (kwargs.search || search || "").toLowerCase();
        limit = kwargs.limit || limit || 8;
        channelId = kwargs.channel_id || channelId;

        /**
         * Returns the given list of partners after filtering it according to
         * the logic of the Python method `get_mention_suggestions` for the
         * given search term. The result is truncated to the given limit and
         * formatted as expected by the original method.
         *
         * @param {ModelRecord[]} partners
         * @param {string} search
         * @param {number} limit
         * @returns {Object[]}
         */
        const mentionSuggestionsFilter = (partners, search, limit) => {
            const matchingPartners = Object.values(
                this.mail_partner_format(
                    partners
                        .filter((partner) => {
                            const [member] = this.env["discuss.channel.member"]._filter([
                                ["channel_id", "=", channelId],
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
                )
            ).map((partnerFormat) => {
                const [member] = this.env["discuss.channel.member"]._filter([
                    ["channel_id", "=", channelId],
                    ["partner_id", "=", partnerFormat.id],
                ]);
                partnerFormat["channelMembers"] = [
                    [
                        "ADD",
                        this.env["discuss.channel.member"]._discussChannelMemberFormat([
                            member.id,
                        ])[0],
                    ],
                ];
                return partnerFormat;
            });
            // reduce results to max limit
            matchingPartners.length = Math.min(matchingPartners.length, limit);
            return matchingPartners;
        };

        // add main suggestions based on users
        const partnersFromUsers = this.env["res.users"]
            ._filter([])
            .map((user) => this._filter([["id", "=", user.partner_id]])[0])
            .filter((partner) => partner);
        const mainMatchingPartners = mentionSuggestionsFilter(partnersFromUsers, search, limit);

        let extraMatchingPartners = [];
        // if not enough results add extra suggestions based on partners
        const remainingLimit = limit - mainMatchingPartners.length;
        if (mainMatchingPartners.length < limit) {
            const partners = this._filter([
                ["id", "not in", mainMatchingPartners.map((partner) => partner.id)],
            ]);
            extraMatchingPartners = mentionSuggestionsFilter(partners, search, remainingLimit);
        }
        return mainMatchingPartners.concat(extraMatchingPartners);
    }

    /**
     * Simulates `im_search` on `res.partner`.
     *
     * @param {string} [name]
     * @param {number} [limit]
     * @param {number[]} [excludedIds]
     * @param {KwArgs<{ excluded_ids: number[]; limit: number; name: string }>} [kwargs]
     */
    im_search(name, limit, excludedIds, kwargs = {}) {
        name = (kwargs.name || name || "").toLowerCase(); // simulates ILIKE
        limit = kwargs.limit || limit || 20;
        excludedIds = kwargs.excluded_ids || excludedIds || [];

        // simulates domain with relational parts (not supported by mock server)
        const matchingPartners = this.env["res.users"]
            ._filter([])
            .filter((user) => {
                const partner = this._filter([["id", "=", user.partner_id]])[0];
                // user must have a partner
                if (!partner) {
                    return false;
                }
                // not current partner
                if (partner.id === this.env.partner_id) {
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
                const partner = this._filter([["id", "=", user.partner_id]])[0];
                return {
                    id: partner.id,
                    name: partner.name,
                };
            })
            .sort((a, b) => (a.name === b.name ? a.id - b.id : a.name > b.name ? 1 : -1));
        matchingPartners.length = Math.min(matchingPartners.length, limit);
        const resultPartners = matchingPartners.filter(
            (partner) => !excludedIds.includes(partner.id)
        );
        return Object.values(this.mail_partner_format(resultPartners.map((partner) => partner.id)));
    }

    /**
     * Simulates `mail_partner_format` on `res.partner`.
     *
     * @param {number[]} ids
     * @returns {Record<string, ModelRecord>}
     */
    mail_partner_format(ids) {
        const partners = this._filter([["id", "in", ids]], {
            active_test: false,
        });
        // Servers is also returning `is_internal_user` but not
        // done here for simplification.
        return Object.fromEntries(
            partners.map((partner) => {
                const users = this.env["res.users"]._filter([["id", "in", partner.user_ids]]);
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
                        write_date: partner.write_date,
                    },
                ];
            })
        );
    }

    /**
     * Simulates `search_for_channel_invite` on `res.partner`.
     *
     * @param {string} [searchTerm]
     * @param {number} [channelId]
     * @param {number} [limit]
     * @param {KwArgs<{ channelId: number; limit: number; search_term: string }>} [kwargs]
     */
    search_for_channel_invite(searchTerm, channelId, limit, kwargs = {}) {
        searchTerm = (kwargs.search_term || searchTerm || "").toLowerCase(); // simulates ILIKE
        channelId = kwargs.channel_id || channelId;
        limit = kwargs.limit || limit || 30;

        // simulates domain with relational parts (not supported by mock server)
        const matchingPartners = Object.values(
            this.mail_partner_format(
                this.env["res.users"]
                    ._filter([])
                    .filter((user) => {
                        const partner = this._filter([["id", "=", user.partner_id]])[0];
                        // user must have a partner
                        if (!partner) {
                            return false;
                        }
                        // not current partner
                        if (partner.id === this.env.partner_id) {
                            return false;
                        }
                        // no name is considered as return all
                        if (!searchTerm) {
                            return true;
                        }
                        if (partner.name && partner.name.toLowerCase().includes(searchTerm)) {
                            return true;
                        }
                        return false;
                    })
                    .map((user) => user.partner_id)
            )
        );
        const count = matchingPartners.length;
        matchingPartners.length = Math.min(count, limit);
        return {
            count,
            partners: matchingPartners,
        };
    }

    /**
     * Simulates `_get_needaction_count` on `res.partner`.
     *
     * @param {number} id
     * @returns {number}
     */
    _getNeedactionCount(id) {
        const partner = this._filter([["id", "=", id]])[0];
        return this.env["mail.notification"]._filter([
            ["res_partner_id", "=", partner.id],
            ["is_read", "=", false],
        ]).length;
    }

    /**
     * Simulates `_message_fetch_failed` on `res.partner`.
     *
     * @param {number} id
     * @returns {Object[]}
     */
    _messageFetchFailed(id) {
        const partner = this._filter([["id", "=", id]], {
            active_test: false,
        })[0];
        const messages = this.env["mail.message"]
            ._filter([
                ["author_id", "=", partner.id],
                ["res_id", "!=", 0],
                ["model", "!=", false],
                ["message_type", "!=", "user_notification"],
            ])
            .filter((message) => {
                // Purpose is to simulate the following domain on mail.message:
                // ['notification_ids.notification_status', 'in', ['bounce', 'exception']],
                // But it's not supported by _filter domain to follow a relation.
                const notifications = this.env["mail.notification"]._filter([
                    ["mail_message_id", "=", message.id],
                    ["notification_status", "in", ["bounce", "exception"]],
                ]);
                return notifications.length > 0;
            });
        return this.env["mail.message"]._messageNotificationFormat(
            messages.map((message) => message.id)
        );
    }
}
