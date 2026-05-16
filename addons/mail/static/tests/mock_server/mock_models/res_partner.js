import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import {
    fields,
    getKwArgs,
    makeKwArgs,
    serverState,
    webModels,
} from "@web/../tests/web_test_helpers";

/** @typedef {import("@web/../tests/web_test_helpers").ModelRecord} ModelRecord */

export class ResPartner extends webModels.ResPartner {
    _inherit = ["mail.thread"];

    description = fields.Char({ string: "Description" });
    hasWriteAccess = fields.Boolean({ default: true });
    message_main_attachment_id = fields.Many2one({
        relation: "ir.attachment",
        string: "Main attachment",
    });
    is_in_call = fields.Boolean({ compute: "_compute_is_in_call" });

    _views = {
        form: /* xml */ `
            <form>
                <sheet>
                    <field name="name"/>
                </sheet>
                <chatter/>
            </form>`,
    };

    _compute_is_in_call() {
        for (const partner of this) {
            partner.is_in_call =
                this.env["discuss.channel.member"].search([
                    ["rtc_session_ids", "!=", []],
                    ["partner_id", "=", partner.id],
                ]).length > 0;
        }
    }

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

        const store = new mailDataHelpers.Store(
            this.browse(mainMatchingPartnerIds.concat(extraMatchingPartnerIds))
        );
        const roleIds = this.env["res.role"].search(
            [["name", "ilike", search || ""]],
            makeKwArgs({ limit: limit || 8 })
        );
        store.add("res.role", this.env["res.role"]._read_format(roleIds, ["name"], false));

        return store.get_result();
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
        /** @type {import("mock_models").DiscussChannel} */
        const channel = this.env["discuss.channel"].browse(channel_id)[0];
        const searchLower = search.toLowerCase();

        const extraDomain = [
            ["user_ids", "!=", false],
            ["active", "=", true],
            ["partner_share", "=", false],
        ];
        const parent_channel = this.browse(channel.parent_channel_id);
        const allowed_group = parent_channel?.group_public_id ?? channel.group_public_id;
        if (allowed_group) {
            extraDomain.push(["group_ids", "in", allowed_group]);
        }
        const baseDomain = search
            ? ["|", ["name", "ilike", searchLower], ["email", "ilike", searchLower]]
            : [];
        const partners = this._search_mention_suggestions(
            baseDomain,
            limit,
            channel_id,
            extraDomain
        );
        const store = new mailDataHelpers.Store();
        const memberIds = DiscussChannelMember.search([
            ["channel_id", "in", [channel.id, channel.parent_channel_id]],
            ["partner_id", "in", partners],
        ]);
        const users = ResUsers.search([["partner_id", "in", partners]]).reduce((map, userId) => {
            const [user] = ResUsers.browse(userId);
            map[user.partner_id] = user;
            return map;
        }, {});
        for (const memberId of memberIds) {
            const [member] = DiscussChannelMember.browse(memberId);
            store.add(this.browse(member.partner_id));
            store.add(
                DiscussChannelMember.browse(member.id),
                makeKwArgs({ fields: ["channel", "persona"] })
            );
        }
        for (const partnerId of partners) {
            const data = {
                name: users[partnerId]?.name,
                group_ids: users[partnerId]?.group_ids.includes(allowed_group)
                    ? allowed_group
                    : undefined,
            };
            store.add(this.browse(partnerId), data);
        }
        const roleIds = this.env["res.role"].search(
            [["name", "ilike", searchLower || ""]],
            makeKwArgs({ limit: limit || 8 })
        );
        store.add("res.role", this.env["res.role"]._read_format(roleIds, ["name"], false));
        return store.get_result();
    }

    compute_im_status(partner) {
        if (partner.im_status) {
            return partner.im_status;
        }
        if (partner.id === serverState.odoobotId) {
            return "bot";
        }
        if (!partner.user_ids.length) {
            return "im_status";
        }
        return "offline";
    }

    /* override */
    _compute_display_name() {
        super._compute_display_name();
        for (const record of this) {
            if (record.parent_id && !record.name) {
                const [parent] = this.env["res.partner"].browse(record.parent_id);
                const type = this._fields.type.selection.find((item) => item[0] === record.type);
                record.display_name = `${parent.name}, ${type[1]}`;
            }
        }
    }

    /**
     * @param {Array} domain
     * @param {number} limit
     * @param {number} channel_id
     * @param {Array} extraDomain
     * @returns {Array}
     */
    _search_mention_suggestions(domain, limit, channel_id, extraDomain) {
        const DiscussChannelMember = this.env["discuss.channel.member"];
        const ResUsers = this.env["res.users"];

        const channel = this.env["discuss.channel"].browse(channel_id)[0];
        let partnerIds = [];
        if (!domain?.length && channel) {
            partnerIds = DiscussChannelMember.search([
                ["channel_id", "in", [channel.id, channel.parent_channel_id]],
            ]).map((memberId) => DiscussChannelMember.browse(memberId)[0].partner_id);
        } else {
            partnerIds = ResUsers.search(domain).map(
                (userId) => ResUsers.browse(userId)[0].partner_id
            );
        }
        if (extraDomain?.length) {
            const usersWithAccess = ResUsers.search(extraDomain).map(
                (userId) => ResUsers.browse(userId)[0].partner_id
            );
            partnerIds.push(...usersWithAccess);
        }
        return Array.from(new Set(partnerIds)).slice(0, limit);
    }

    /**
     * @param {number[]} ids
     * @returns {Record<string, ModelRecord>}
     */
    _to_store(store, fields, extra_fields) {
        const kwargs = getKwArgs(arguments, "store", "fields", "extra_fields");
        fields = kwargs.fields;
        extra_fields = kwargs.extra_fields ?? [];
        fields = fields.concat(extra_fields);

        /** @type {import("mock_models").ResCountry} */
        const ResCountry = this.env["res.country"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        this._compute_main_user_id(); // compute not automatically triggering when necessary
        store._add_record_fields(
            this,
            fields.filter(
                (field) =>
                    ![
                        "avatar_128",
                        "country_id",
                        "display_name",
                        "is_admin",
                        "notification_type",
                        "signature",
                        "user",
                    ].includes(field)
            )
        );
        for (const partner of this) {
            const data = {};
            if (fields.includes("avatar_128")) {
                data.avatar_128_access_token = partner.id;
                data.write_date = partner.write_date;
            }
            if (fields.includes("country_id")) {
                const [country_id] = ResCountry.browse(partner.country_id);
                data.country_id = country_id || false;
            }
            if (fields.includes("display_name")) {
                data.displayName = partner.display_name || partner.name;
            }
            if (fields.includes("im_status")) {
                data.im_status = this.compute_im_status(partner);
                data.im_status_access_token = partner.id;
            }
            if (fields.includes("user")) {
                data.main_user_id = partner.main_user_id;
                if (partner.main_user_id) {
                    store._add_record_fields(ResUsers.browse(partner.main_user_id), ["share"]);
                }
                if (partner.main_user_id && fields.includes("is_admin")) {
                    const users = ResUsers.search([["login", "=", "admin"]]);
                    store._add_record_fields(ResUsers.browse(partner.main_user_id), {
                        is_admin:
                            this.env.cookie.get("authenticated_user_sid") ===
                                (Number.isInteger(users?.[0]) ? users?.[0] : users?.[0]?.id) ??
                            false,
                    }); // mock server simplification
                }
                if (partner.main_user_id && fields.includes("notification_type")) {
                    store._add_record_fields(
                        ResUsers.browse(partner.main_user_id),
                        makeKwArgs({ fields: ["notification_type"] })
                    );
                }
                if (partner.main_user_id && fields.includes("signature")) {
                    store._add_record_fields(
                        ResUsers.browse(partner.main_user_id),
                        makeKwArgs({ fields: ["signature"] })
                    );
                }
            }
            if (Object.keys(data).length) {
                store._add_record_fields(this.browse(partner.id), data);
            }
        }
    }

    get _to_store_defaults() {
        return [
            "avatar_128",
            "name",
            "email",
            "active",
            "im_status",
            "is_company",
            mailDataHelpers.Store.one("main_user_id", ["share"]),
        ];
    }

    /**
     * @param {string} [search_term]
     * @param {number} [channel_id]
     * @param {number} [limit]
     */
    search_for_channel_invite(search_term, channel_id, limit = 30) {
        const kwargs = getKwArgs(arguments, "search_term", "channel_id", "limit");
        const store = new mailDataHelpers.Store();
        const channel_invites = this._search_for_channel_invite(
            store,
            kwargs.search_term,
            kwargs.channel_id,
            kwargs.limit
        );
        return { store_data: store.get_result(), ...channel_invites };
    }

    /**
     * @param {string} [search_term]
     * @param {number} [channel_id]
     * @param {number} [limit]
     */
    _search_for_channel_invite(store, search_term, channel_id, limit = 30) {
        const kwargs = getKwArgs(arguments, "store", "search_term", "channel_id", "limit");
        search_term = kwargs.search_term || "";
        channel_id = kwargs.channel_id;
        limit = kwargs.limit || 30;

        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        search_term = search_term.toLowerCase(); // simulates ILIKE
        let memberPartnerIds;
        if (channel_id) {
            memberPartnerIds = new Set(
                DiscussChannelMember._filter([["channel_id", "=", channel_id]]).map(
                    (member) => member.partner_id
                )
            );
        }
        // simulates domain with relational parts (not supported by mock server)
        const matchingPartnersIds = ResUsers._filter([])
            .filter((user) => {
                const [partner] = this.browse(user.partner_id);
                // user must have a partner
                if (!partner) {
                    return false;
                }
                // not current partner
                if (!channel_id && partner.id === this.env.user.partner_id) {
                    return false;
                }
                // user should not already be a member of the channel
                if (channel_id && memberPartnerIds.has(partner.id)) {
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
            .reduce((ids, partnerId) => {
                if (!ids.includes(partnerId)) {
                    ids.push(partnerId);
                }
                return ids;
            }, []);
        const count = matchingPartnersIds.length;
        matchingPartnersIds.length = Math.min(count, limit);
        this._search_for_channel_invite_to_store(matchingPartnersIds, store, channel_id);
        return {
            count,
            partner_ids: matchingPartnersIds,
        };
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

    _get_store_avatar_card_fields() {
        return ["email", "partner_share", "name", "phone"];
    }
}
