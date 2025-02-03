import { parseEmail } from "@mail/utils/common/format";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { _t } from "@web/core/l10n/translation";
import { TagsList } from "@web/core/tags_list/tags_list";
import { isEmail } from "@web/core/utils/strings";
import { useService } from "@web/core/utils/hooks";
import { useOpenMany2XRecord, useSelectCreate } from "@web/views/fields/relational_utils";

import { Component, useEffect, useState } from "@odoo/owl";

export class RecipientsInput extends Component {
    static template = "mail.RecipientsInput";
    static components = { AutoComplete, TagsList };
    static props = {
        thread: { type: Object },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            tags: this.getTagsFromMailThread(),
        });

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
                    lang: partner.data.lang,
                    name: partner.data.name,
                    partner_id: partner.resId,
                    persona: { type: "partner", id: partner.resId },
                });
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
                        lang: partner.lang,
                        name: partner.name,
                        partner_id: partner.id,
                        persona: { type: "partner", id: partner.id },
                    });
                }
            },
        });

        useEffect(
            () => {
                this.state.tags = this.getTagsFromMailThread();
            },
            () => [
                this.props.thread.suggestedRecipients,
                this.props.thread.suggestedRecipients.length,
                this.props.thread.additionalRecipients,
                this.props.thread.additionalRecipients.length,
            ]
        );
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

                    if (isEmail(email)) {
                        options.push({
                            id: 0,
                            label: term,
                            onSelectOption: async () => {
                                const partners = await this.orm.searchRead(
                                    "res.partner",
                                    [["email", "=", email]],
                                    ["email", "id", "lang", "name"],
                                    { limit: 1 }
                                );
                                if (partners.length) {
                                    const partner = partners[0];
                                    this.insertAdditionalRecipient({
                                        email: partner.email,
                                        lang: partner.lang,
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
                            },
                        });
                    }

                    const limit = 8;
                    const matches = await this.orm.searchRead(
                        "res.partner",
                        [
                            ["id", "not in", Array.from(partnerIds)],
                            "|",
                            ["name", "ilike", term],
                            ["email", "ilike", term],
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
                                    lang: match.lang,
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

                    if (name) {
                        options.push({
                            label: _t("Create and edit..."),
                            classList: "o_m2o_dropdown_option o_m2o_dropdown_option_create_edit",
                            onSelectOption: () => {
                                const context = {
                                    form_view_ref: "base.view_partner_simple_form",
                                    default_name: name,
                                    default_email: email,
                                };
                                this.openFormViewToCreateResPartner({ context });
                            },
                        });
                    }

                    return options;
                },
            },
        ];
    }

    /** @returns {Object} */
    getTagsFromMailThread() {
        const tags = [];
        for (const recipient of this.props.thread.suggestedRecipients) {
            tags.push({
                id: recipient.partner_id,
                text: recipient.name,
                onDelete: () => {
                    this.props.thread.suggestedRecipients =
                        this.props.thread.suggestedRecipients.filter(
                            (suggestedRecipient) =>
                                suggestedRecipient.partner_id !== recipient.partner_id
                        );
                },
            });
        }
        for (const recipient of this.props.thread.additionalRecipients) {
            tags.push({
                id: recipient.partner_id,
                text: recipient.name,
                onDelete: () => {
                    this.props.thread.additionalRecipients =
                        this.props.thread.additionalRecipients.filter(
                            (additionalRecipient) =>
                                additionalRecipient.partner_id !== recipient.partner_id
                        );
                },
            });
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
        const options = Object.getPrototypeOf(option);
        options.onSelectOption?.();
    }
}
