import { parseEmail } from "@mail/utils/common/format";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { _t } from "@web/core/l10n/translation";
import { isEmail } from "@web/core/utils/strings";
import { useService } from "@web/core/utils/hooks";
import { useSelectCreate } from "@web/views/fields/relational_utils";

import { rpc } from "@web/core/network/rpc";
import { usePopover } from "@web/core/popover/popover_hook";
import { useTagNavigation } from "@web/core/record_selectors/tag_navigation_hook";
import { uniqueId } from "@web/core/utils/functions";
import { RecipientsPopover } from "./recipients_popover";
import { RecipientsInputTagsList } from "./recipients_input_tags_list";

import { Component } from "@odoo/owl";

export class RecipientsInput extends Component {
    static template = "mail.RecipientsInput";
    static components = { AutoComplete, RecipientsInputTagsList };
    static props = {
        thread: { type: Object },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.store = useService("mail.store");
        this.popover = usePopover(RecipientsPopover, { position: "bottom-middle" });
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
        const tags = this.getTagsFromMailThread();
        if (tags[index]) {
            tags[index].onDelete();
        }
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
                    const [name, email] = term ? parseEmail(term) : ["", ""];

                    const limit = 8;
                    const matches = await this.orm.searchRead(
                        "res.partner",
                        [
                            ["id", "not in", Array.from(partnerIds)],
                            "|",
                            ["name", "ilike", name],
                            email ? ["email_normalized", "ilike", email] : [0, "=", 1], // if no email, use a false leaf
                        ],
                        ["email", "id", "lang", "name"],
                        { limit }
                    );

                    options.push(
                        ...matches.map((match) => ({
                            label: match.email
                                ? _t("%(partner_name)s <%(partner_email)s>", {
                                      partner_name: match.name || _t("Unnamed"),
                                      partner_email: match.email,
                                  })
                                : match.name || _t("Unnamed"),
                            onSelect: () => {
                                this.insertAdditionalRecipient({
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
                    options.push(createOption);
                    return options;
                },
            },
        ];
    }

    /** @returns {Object} */
    getTagsFromMailThread() {
        const tags = [];
        const createTagForRecipient = (recipient, recipientField) => {
            const title = `${recipient.name || _t("Unnamed")} ${
                recipient.email ? "<" + recipient.email + ">" : ""
            }`;
            title.trim();
            tags.push({
                id: uniqueId("tag_"),
                resId: recipient.partner_id,
                canEdit: true,
                text: recipient.name || recipient.email || _t("Unnamed"),
                name: recipient.name || _t("Unnamed"),
                email: recipient.email,
                title,
                onClick: (ev) => {
                    if (recipient.partner_id && recipient.email) {
                        const viewProfileBtnOverride = () => {
                            const action = {
                                type: "ir.actions.act_window",
                                res_model: "res.partner",
                                res_id: recipient.partner_id,
                                views: [[false, "form"]],
                                target: "current",
                            };
                            this.action.doAction(action);
                        };
                        this.popover.open(ev.target, {
                            viewProfileBtnOverride,
                            id: recipient.partner_id,
                        });
                    }
                },
                onDelete: () => {
                    this.props.thread[recipientField] = this.props.thread[recipientField].filter(
                        (additionalOrSuggestedRecipient) =>
                            additionalOrSuggestedRecipient.partner_id !== recipient.partner_id ||
                            additionalOrSuggestedRecipient.email !== recipient.email
                    );
                },
            });
        };
        for (const recipient of this.props.thread.suggestedRecipients) {
            createTagForRecipient(recipient, "suggestedRecipients");
        }
        for (const recipient of this.props.thread.additionalRecipients) {
            createTagForRecipient(recipient, "additionalRecipients");
        }
        return tags;
    }

    /** @return {Array[SuggestedRecipient]}*/
    getAllMailThreadRecipients() {
        return [
            ...this.props.thread.suggestedRecipients,
            ...this.props.thread.additionalRecipients,
        ];
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

    /**
     * @param {SuggestedRecipient} recipient
     * @returns {boolean}
     */
    hasRecipient(recipient) {
        return this.getAllMailThreadRecipients().some(
            (current) => current.email === recipient.email
        );
    }

    /** @param {SuggestedRecipient} recipient */
    insertAdditionalRecipient(recipient) {
        if (this.hasRecipient(recipient)) {
            return;
        }
        this.props.thread.additionalRecipients.push(recipient);
    }

    /** @returns {string} */
    getPlaceholder() {
        const hasRecipients =
            this.props.thread.suggestedRecipients.length ||
            this.props.thread.additionalRecipients.length;
        return hasRecipients ? "" : _t("Followers only");
    }
}
