import { parseEmail } from "@mail/utils/common/format";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { _t } from "@web/core/l10n/translation";
import { isEmail } from "@web/core/utils/strings";
import { highlightText, odoomark } from "@web/core/utils/html";
import { useService } from "@web/core/utils/hooks";
import { useSelectCreate } from "@web/views/fields/relational_utils";
import { BadgeTag } from "@web/core/tags_list/badge_tag";

import { rpc } from "@web/core/network/rpc";
import { useTagNavigation } from "@web/core/record_selectors/tag_navigation_hook";
import { uniqueId } from "@web/core/utils/functions";
import { RecipientTag, useRecipientChecker } from "./recipient_tag";

import { Component, computed, props, types } from "@odoo/owl";

export class RecipientsInput extends Component {
    static template = "mail.RecipientsInput";
    static components = { AutoComplete, RecipientTag, BadgeTag };

    setup() {
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.props = props({
            thread: types.instanceOf(this.store["mail.thread"].Class),
            recipientType: types.string(),
            placeholder: types.string(),
        });
        this.tags = computed(() => this.getTagsFromMailThread());
        this.recipientCheckerBus = useRecipientChecker(this.tags);
        useTagNavigation("recipientsInputRef", {
            delete: this.deleteTagByIndex.bind(this),
        });

        this.openListViewToSelectResPartner = useSelectCreate({
            resModel: "res.partner",
            activeActions: {
                create: false,
                link: true, // Unable multi-select
            },
            /** @param {Object} resIds */
            onSelected: async (resIds) => {
                const partners = await this.orm.searchRead(
                    "res.partner",
                    [["id", "in", Array.from(resIds)]],
                    ["email", "id", "lang", "name"]
                );
                for (const partner of partners) {
                    this.insertAdditionalRecipient({
                        email: partner.email,
                        name: partner.name,
                        partner_id: partner.id,
                    });
                }
            },
        });
    }

    deleteTagByIndex(index) {
        this.tags()[index]?.onDelete();
    }

    getAutoCompleteSources() {
        return [
            {
                placeholder: _t("Loading..."),
                /** @param {string} term */
                options: async (term) => {
                    const partnerIds = new Set();
                    const recipients = this.getAllMailThreadRecipients();

                    for (const recipient of recipients) {
                        if (recipient.partner_id) {
                            partnerIds.add(recipient.partner_id);
                        }
                    }

                    const options = [];

                    const limit = 8;
                    const matches = await this.orm.call("res.partner", "web_name_search", [], {
                        name: term,
                        specification: {
                            email: {},
                            lang: {},
                            name: {},
                            parent_name: {},
                            display_name: {},
                        },
                        limit,
                        domain: [["id", "not in", Array.from(partnerIds)]],
                        context: { show_email: true },
                    });

                    options.push(
                        ...matches.map((match) => ({
                            label: match.display_name
                                ? highlightText(
                                      term,
                                      odoomark(match.__formatted_display_name),
                                      "fw-bolder text-primary"
                                  )
                                : _t("Unnamed"),
                            onSelect: () => {
                                this.insertAdditionalRecipient({
                                    display_name: match.display_name,
                                    email: match.email,
                                    name: match.name,
                                    partner_id: match.id,
                                });
                            },
                        }))
                    );

                    if (matches.length >= limit) {
                        options.push({
                            label: _t("Search More..."),
                            cssClass: "o_m2o_dropdown_option o_m2o_dropdown_option_search_more",
                            onSelect: () => {
                                this.openListViewToSelectResPartner({});
                            },
                        });
                    }

                    const [name, email] = term ? parseEmail(term) : ["", ""];
                    const createOption = {
                        cssClass: "o_m2o_dropdown_option o_m2o_dropdown_option_create",
                        label: _t("Create %s", name),
                    };

                    if (isEmail(email)) {
                        createOption.onSelect = async () => {
                            const partners = await rpc("/mail/partner/from_email", {
                                thread_model: this.props.thread.model,
                                thread_id: this.props.thread.id,
                                emails: [term],
                            });
                            if (partners.length) {
                                const partner = partners[0];
                                this.insertAdditionalRecipient({
                                    email: partner.email,
                                    name: partner.name,
                                    partner_id: partner.id,
                                });
                            } else {
                                this.insertAdditionalRecipient({
                                    email,
                                    name,
                                    partner_id: false,
                                });
                            }
                        };
                    } else {
                        createOption.onSelect = async () => {
                            const [partnerId] = await this.orm.create("res.partner", [
                                { name, email },
                            ]);
                            this.insertAdditionalRecipient({
                                email,
                                name,
                                partner_id: partnerId,
                            });
                        };
                    }
                    if (name.trim() || email) {
                        options.push(createOption);
                    }
                    return options;
                },
            },
        ];
    }

    get otherFollowersCount() {
        return this.props.thread.selfFollower
            ? this.props.thread.followersCount - 1
            : this.props.thread.followersCount;
    }

    get followersBadge() {
        const text =
            this.otherFollowersCount === 1
                ? _t("1 Follower")
                : _t("%(followersCount)s Followers", { followersCount: this.otherFollowersCount });
        return {
            color: 4,
            text,
            tooltip: this.props.thread.followers
                .map((f) => {
                    const email = f.partner_id.displayEmail;
                    return `${this.props.thread.getPersonaName(f.partner_id) || _t("Unnamed")} ${
                        email ? "<" + email + ">" : ""
                    }`;
                })
                .join("\n"),
        };
    }

    /** @returns {Object} */
    getTagsFromMailThread() {
        const tags = [];
        const createTagForRecipient = (recipient, recipientField) => {
            const tooltip = `${recipient.name || recipient.display_name || _t("Unnamed")} ${
                recipient.email ? "<" + recipient.email + ">" : ""
            }`;
            tooltip.trim();
            tags.push({
                id: uniqueId("tag_"),
                resId: recipient.partner_id,
                text: recipient.name || recipient.display_name || recipient.email || _t("Unnamed"),
                name: recipient.name || recipient.display_name || _t("Unnamed"),
                email: recipient.email || "",
                tooltip,
                onDelete: () => {
                    this.props.thread[recipientField] = this.props.thread[recipientField].filter(
                        (additionalOrSuggestedRecipient) =>
                            additionalOrSuggestedRecipient.partner_id !== recipient.partner_id ||
                            additionalOrSuggestedRecipient.email !== recipient.email
                    );
                },
                updateRecipient: this.updateRecipient.bind(this),
                bus: this.recipientCheckerBus,
            });
        };
        for (const recipientField of ["suggestedRecipients", "additionalRecipients"]) {
            for (const recipient of this.props.thread[recipientField].filter(
                (r) => r.recipient_type === this.props.recipientType
            )) {
                createTagForRecipient(recipient, recipientField);
            }
        }
        return tags;
    }

    /** @return {Array[SuggestedRecipient]}*/
    getAllMailThreadRecipients() {
        return [
            ...this.props.thread.suggestedRecipients,
            ...this.props.thread.additionalRecipients,
        ].filter((r) => r.recipient_type === this.props.recipientType);
    }

    /**
     * This method updates a recipient with a new email address.
     * @param {string} emailNormalized email address to be set on the partner. The address is not a mailbox
     * notation and only address, e.g. "Raoulette <raoulette@gmail.com>" is not accepted but "raoulette@gmail.com"
     * is accepted as input.
     * @param {number} recipientPartnerId ID of the partner to update
     */
    async updateRecipient(emailNormalized, recipientPartnerId) {
        await this.orm.write("res.partner", [recipientPartnerId], { email: emailNormalized });
        const allRecipients = this.getAllMailThreadRecipients();
        allRecipients.some((oldRecipient) => {
            if (oldRecipient.partner_id === recipientPartnerId) {
                oldRecipient.email = emailNormalized;
                return true;
            }
        });
    }

    /** @param {SuggestedRecipient} recipient */
    insertAdditionalRecipient(recipient) {
        this.props.thread.additionalRecipients.push({
            ...recipient,
            recipient_type: this.props.recipientType,
        });
    }

    /** @returns {string} */
    getPlaceholder() {
        return this.getAllMailThreadRecipients().length ? "" : this.props.placeholder;
    }
}
