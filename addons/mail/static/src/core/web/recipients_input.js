import { parseEmail } from "@mail/utils/common/format";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { _t } from "@web/core/l10n/translation";
import { TagsList } from "@web/core/tags_list/tags_list";
import { isEmail } from "@web/core/utils/strings";
import { useService } from "@web/core/utils/hooks";
import { useOpenMany2XRecord, useSelectCreate } from "@web/views/fields/relational_utils";

import { Component } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class RecipientsInput extends Component {
    static template = "mail.RecipientsInput";
    static components = { AutoComplete, TagsList };
    static props = {
        thread: { type: Object },
    };

    setup() {
        this.orm = useService("orm");
        this.openFormViewToCreateResPartner = useOpenMany2XRecord({
            fieldString: _t("Additional Contact"),
            resModel: "res.partner",
            activeActions: {
                create: true,
            },
            /** @param {Record} partner */
            onRecordSaved: async (partner) => {
                this.insertAdditionalRecipient({
                    email: partner.data.email,
                    name: partner.data.name,
                    partner_id: partner.resId,
                    persona: { type: "partner", id: partner.resId },
                });
            },
        });

        this.openFormViewToEditPartner = useOpenMany2XRecord({
            fieldString: _t("Edit Partner"),
            resModel: "res.partner",
            activeActions: {
                create: false,
                createEdit: false,
                write: true,
            },
            /** @param {Record} partner */
            onRecordSaved: (partner) => {
                const recipients = this.getAllMailThreadRecipients().filter(
                    (recipient) => recipient.partner_id === partner.resId
                );
                for (const recipient of recipients) {
                    Object.assign(recipient, {
                        email: partner.data.email,
                        name: partner.data.name,
                    });
                }
            },
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
                        persona: { type: "partner", id: partner.id },
                    });
                }
            },
        });
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
                            id: match.id,
                            label: match.email
                                ? _t("%(partner_name)s <%(partner_email)s>", {
                                      partner_name: match.name,
                                      partner_email: match.email,
                                  })
                                : match.name,
                            onSelectOption: () => {
                                this.insertAdditionalRecipient({
                                    email: match.email,
                                    name: match.name,
                                    partner_id: match.id,
                                    persona: { type: "partner", id: match.id },
                                });
                            },
                        }))
                    );

                    if (matches.length >= limit) {
                        options.push({
                            label: _t("Search More..."),
                            classList: "o_m2o_dropdown_option o_m2o_dropdown_option_search_more",
                            onSelectOption: () => {
                                this.openListViewToSelectResPartner({});
                            },
                        });
                    }

                    const createOption = {
                        classList: "o_m2o_dropdown_option o_m2o_dropdown_option_create",
                        label: _t("Create %s", name),
                    };

                    if (isEmail(email)) {
                        createOption.onSelectOption = async () => {
                            const partners = await rpc("/mail/partner/from_email", {
                                thread_model: this.props.thread.model,
                                thread_id: this.props.thread.id,
                                emails: [email],
                            });
                            if (partners.length) {
                                const partner = partners[0];
                                this.insertAdditionalRecipient({
                                    email: partner.email,
                                    name: partner.name,
                                    partner_id: partner.id,
                                    persona: { type: "partner", id: partner.id },
                                });
                            } else {
                                this.insertAdditionalRecipient({
                                    email,
                                    name,
                                    partner_id: false,
                                    persona: false,
                                });
                            }
                        };
                    } else {
                        createOption.onSelectOption = () => {
                            const context = {
                                form_view_ref: "base.view_partner_simple_form",
                                default_name: name,
                                default_email: email,
                            };
                            this.openFormViewToCreateResPartner({ context });
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
            const title = _t("%(partner_name)s <%(partner_email)s>", {
                partner_name: recipient.name,
                partner_email: recipient.email,
            });
            tags.push({
                id: recipient.partner_id,
                canEdit: true,
                text: recipient.name || recipient.email,
                title,
                onClick: () => {
                    if (recipient.partner_id) {
                        this.openFormViewToEditPartner({
                            resId: recipient.partner_id,
                            title: _t("Edit: %s", recipient.name),
                            context: {
                                form_view_ref: "base.view_partner_simple_form",
                            },
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

    /** @param {Object} option */
    onSelect(option) {
        option.onSelectOption?.();
    }
}
