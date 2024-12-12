import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { fields, getKwArgs, makeKwArgs, webModels } from "@web/../tests/web_test_helpers";
import { DEFAULT_MAIL_SEARCH_ID, DEFAULT_MAIL_VIEW_ID } from "./constants";

/** @typedef {import("@web/../tests/web_test_helpers").ModelRecord} ModelRecord */

export class ResPartner extends webModels.ResPartner {
    _inherit = ["mail.thread"];

    description = fields.Char({ string: "Description" });
    hasWriteAccess = fields.Boolean({ default: true });
    message_main_attachment_id = fields.Many2one({
        relation: "ir.attachment",
        string: "Main attachment",
    });

    _views = {
        [`search, ${DEFAULT_MAIL_SEARCH_ID}`]: /* xml */ `<search/>`,
        [`form,${DEFAULT_MAIL_VIEW_ID}`]: /* xml */ `
            <form>
                <sheet>
                    <field name="name"/>
                </sheet>
                <chatter/>
            </form>`,
    };

    /**
     * @param {string} [search]
     * @param {number} [limit]
     */
    get_mention_suggestions(search, limit = 8) {
        const kwargs = getKwArgs(arguments, "search", "limit");
        search = kwargs.search || "";
        limit = kwargs.limit || 8;

        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        search = search.toLowerCase();
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
            const matchingPartnerIds = partners
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
                .map((partner) => partner.id);
            // reduce results to max limit
            matchingPartnerIds.length = Math.min(matchingPartnerIds.length, limit);
            return matchingPartnerIds;
        };

        // add main suggestions based on users
        const partnersFromUsers = ResUsers._filter([])
            .map((user) => this.browse(user.partner_id)[0])
            .filter((partner) => partner);
        const mainMatchingPartnerIds = mentionSuggestionsFilter(partnersFromUsers, search, limit);

        let extraMatchingPartnerIds = [];
        // if not enough results add extra suggestions based on partners
        const remainingLimit = limit - mainMatchingPartnerIds.length;
        if (mainMatchingPartnerIds.length < limit) {
            const partners = this._filter([["id", "not in", mainMatchingPartnerIds]]);
            extraMatchingPartnerIds = mentionSuggestionsFilter(partners, search, remainingLimit);
        }
        return new mailDataHelpers.Store(
            this.browse(mainMatchingPartnerIds.concat(extraMatchingPartnerIds))
        ).get_result();
    }

    /**
     * @param {number} [channel_id]
     * @param {string} [search]
     * @param {number} [limit]
     */
    get_mention_suggestions_from_channel(channel_id, search, limit = 8) {
        const kwargs = getKwArgs(arguments, "channel_id", "search", "limit");
        channel_id = kwargs.channel_id;
        search = kwargs.search || "";
        limit = kwargs.limit || 8;

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        search = search.toLowerCase();
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
            const matchingPartners = partners.filter((partner) => {
                const [member] = DiscussChannelMember._filter([
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
            });
            // reduce results to max limit
            matchingPartners.length = Math.min(matchingPartners.length, limit);
            return matchingPartners;
        };

        // add main suggestions based on users
        const partnersFromUsers = ResUsers._filter([])
            .map((user) => this.browse(user.partner_id)[0])
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
        const store = new mailDataHelpers.Store();
        for (const partner of mainMatchingPartners.concat(extraMatchingPartners)) {
            store.add(this.browse(partner.id));
            const [member] = DiscussChannelMember._filter([
                ["channel_id", "=", channel_id],
                ["partner_id", "=", partner.id],
            ]);
            store.add(
                DiscussChannelMember.browse(member.id),
                makeKwArgs({ fields: { channel: [], persona: [] } })
            );
        }
        return store.get_result();
    }

    /**
     * @param {string} [name]
     * @param {number} [limit = 20]
     * @param {number[]} [excluded_ids]
     */
    im_search(name, limit = 20, excluded_ids) {
        const kwargs = getKwArgs(arguments, "name", "limit", "excluded_ids");
        name = kwargs.name || "";
        limit = kwargs.limit || 20;
        excluded_ids = kwargs.excluded_ids || [];

        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        name = name.toLowerCase(); // simulates ILIKE
        // simulates domain with relational parts (not supported by mock server)
        const matchingPartnersIds = ResUsers._filter([])
            .filter((user) => {
                const [partner] = this.browse(user.partner_id);
                // user must have a partner
                if (!partner) {
                    return false;
                }
                // not excluded
                if (excluded_ids.includes(partner.id)) {
                    return false;
                }
                // not current partner
                if (partner.id === this.env.user.partner_id) {
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
            .map((user) => user.partner_id)
            .sort((a, b) => (a.name === b.name ? a.id - b.id : a.name > b.name ? 1 : -1));
        matchingPartnersIds.length = Math.min(matchingPartnersIds.length, limit);
        return new mailDataHelpers.Store(this.browse(matchingPartnersIds)).get_result();
    }

    /**
     * @param {number[]} ids
     * @returns {Record<string, ModelRecord>}
     */
    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "id", "store", "fields");
        fields = kwargs.fields;
        if (!fields) {
            fields = ["avatar_128", "name", "email", "active", "im_status", "is_company", "user"];
        }

        /** @type {import("mock_models").ResCountry} */
        const ResCountry = this.env["res.country"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        for (const partner of this.browse(ids)) {
            const [data] = this._read_format(
                partner.id,
                fields.filter(
                    (field) =>
                        ![
                            "avatar_128",
                            "country",
                            "display_name",
                            "isAdmin",
                            "notification_type",
                            "user",
                        ].includes(field)
                ),
                false
            );
            if (fields.includes("avatar_128")) {
                data.avatar_128_access_token = partner.id;
                data.write_date = partner.write_date;
            }
            if (fields.includes("country")) {
                const [country] = ResCountry.browse(partner.country_id);
                data.country = country
                    ? {
                          code: country.code,
                          id: country.id,
                          name: country.name,
                      }
                    : false;
            }
            if (fields.includes("display_name")) {
                data.displayName = partner.display_name || partner.name;
            }
            if (fields.includes("user")) {
                const users = ResUsers.browse(partner.user_ids);
                const internalUsers = users.filter((user) => !user.share);
                let mainUser;
                if (internalUsers.length > 0) {
                    mainUser = internalUsers[0];
                } else if (users.length > 0) {
                    mainUser = users[0];
                }
                data.userId = mainUser ? mainUser.id : false;
                data.isInternalUser = mainUser ? !mainUser.share : false;
                if (fields.includes("isAdmin")) {
                    data.isAdmin = true; // mock server simplification
                }
                if (fields.includes("notification_type")) {
                    data.notification_preference = mainUser.notification_type;
                }
            }
            store.add(this.browse(partner.id), data);
        }
    }

    /**
     * @param {string} [search_term]
     * @param {number} [channel_id]
     * @param {number} [limit]
     */
    search_for_channel_invite(search_term, channel_id, limit = 30) {
        const kwargs = getKwArgs(arguments, "search_term", "channel_id", "limit");
        search_term = kwargs.search_term || "";
        channel_id = kwargs.channel_id;
        limit = kwargs.limit || 30;

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        search_term = search_term.toLowerCase(); // simulates ILIKE
        const memberPartnerIds = new Set(
            DiscussChannelMember._filter([["channel_id", "=", channel_id]]).map(
                (member) => member.partner_id
            )
        );
        // simulates domain with relational parts (not supported by mock server)
        const matchingPartnersIds = ResUsers._filter([])
            .filter((user) => {
                const [partner] = this.browse(user.partner_id);
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
            .map((user) => user.partner_id);
        const count = matchingPartnersIds.length;
        matchingPartnersIds.length = Math.min(count, limit);
        const store = new mailDataHelpers.Store();
        this._search_for_channel_invite_to_store(matchingPartnersIds, store, channel_id);
        return { count, data: store.get_result() };
    }

    _search_for_channel_invite_to_store(ids, store, channel_id) {
        store.add(this.browse(ids));
    }

    /**
     * @param {number} id
     * @returns {number}
     */
    _get_needaction_count(id) {
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];

        const [partner] = this.browse(id);
        return MailNotification._filter([
            ["res_partner_id", "=", partner.id],
            ["is_read", "=", false],
        ]).length;
    }

    _get_current_persona() {
        /** @type {import("mock_models").MailGuest} */
        const MailGuest = this.env["mail.guest"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        if (ResUsers._is_public(this.env.uid)) {
            return [null, MailGuest._get_guest_from_context()];
        }
        return [this.browse(this.env.user.partner_id)[0], null];
    }
}
