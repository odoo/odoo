import { fields, getKwArgs, webModels } from "@web/../tests/web_test_helpers";
import { DEFAULT_MAIL_SEARCH_ID, DEFAULT_MAIL_VIEW_ID } from "./constants";

/** @typedef {import("@web/../tests/web_test_helpers").ModelRecord} ModelRecord */

export class ResPartner extends webModels.ResPartner {
    _inherit = ["mail.thread"];

    description = fields.Char({ string: "Description" });
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
        return mainMatchingPartners.concat(extraMatchingPartners);
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
            const matchingPartners = Object.values(
                this.mail_partner_format(
                    partners
                        .filter((partner) => {
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
                        })
                        .map((partner) => partner.id)
                )
            ).map((partnerFormat) => {
                const [member] = DiscussChannelMember._filter([
                    ["channel_id", "=", channel_id],
                    ["partner_id", "=", partnerFormat.id],
                ]);
                partnerFormat["channelMembers"] = [
                    ["ADD", DiscussChannelMember._discuss_channel_member_format([member.id])[0]],
                ];
                return partnerFormat;
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
        return mainMatchingPartners.concat(extraMatchingPartners);
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
        const matchingPartners = ResUsers._filter([])
            .filter((user) => {
                const [partner] = this.browse(user.partner_id);
                // user must have a partner
                if (!partner) {
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
            .map((user) => {
                const [partner] = this.browse(user.partner_id);
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
        return Object.values(this.mail_partner_format(resultPartners.map((partner) => partner.id)));
    }
    compute_im_status(partner) {
        return partner.im_status;
    }
    /**
     * @param {number[]} ids
     * @returns {Record<string, ModelRecord>}
     */
    mail_partner_format(ids) {
        /** @type {import("mock_models").ResUsers} */
        const ResUsers = this.env["res.users"];

        const partners = this.browse(ids);
        return Object.fromEntries(
            partners.map((partner) => {
                const users = ResUsers.browse(partner.user_ids);
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
                        im_status: this.compute_im_status(partner),
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
        const matchingPartners = Object.values(
            this.mail_partner_format(
                ResUsers._filter([])
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

    /**
     * @param {number} id
     * @returns {Object[]}
     */
    _message_fetch_failed(id) {
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").MailNotification} */
        const MailNotification = this.env["mail.notification"];

        const [partner] = this.browse(id);
        const messages = MailMessage._filter([
            ["author_id", "=", partner.id],
            ["res_id", "!=", 0],
            ["model", "!=", false],
            ["message_type", "!=", "user_notification"],
        ]).filter((message) => {
            // Purpose is to simulate the following domain on mail.message:
            // ['notification_ids.notification_status', 'in', ['bounce', 'exception']],
            // But it's not supported by _filter domain to follow a relation.
            const notifications = MailNotification._filter([
                ["mail_message_id", "=", message.id],
                ["notification_status", "in", ["bounce", "exception"]],
            ]);
            return notifications.length > 0;
        });
        return MailMessage._message_notification_format(messages.map((message) => message.id));
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
