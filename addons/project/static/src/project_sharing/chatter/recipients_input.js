import { RecipientsInput } from "@mail/core/web/recipients_input";
import { patch } from "@web/core/utils/patch";

patch(RecipientsInput.prototype, {

    formatSuggestionLabel({ name, parent_name, email }) {
        let label = parent_name ? `${parent_name} \t --${name || ""}--` : name || "";
        if (email) {
            label = `${label} \t --${email}--`;
        }
        return label;
    },

    async fetchRecipientSuggestions(term, partnerIds) {
        const data = await this.orm.call(
            this.props.thread.model,
            "get_recipient_suggestions",
            [this.props.thread.id],
            { search: term || "" }
        );
        this.store.insert(data);
        return (data["res.partner"] || [])
            .filter((row) => !partnerIds.has(row.id))
            .map((row) => ({
                ...row,
                display_name: row.name,
                __formatted_display_name: this.formatSuggestionLabel(row),
            }));
    },

    insertAdditionalRecipient(recipient) {
        super.insertAdditionalRecipient({
            ...recipient,
            persona: this.store["res.partner"].get(recipient.partner_id)
        });
    },

    // Base always appends a "Create ..." option. Portal users cannot create
    // partners, so remove that option after the shared suggestion fetch runs.
    getAutoCompleteSources() {
        const [source] = super.getAutoCompleteSources();
        return [
            {
                ...source,
                options: async (term) => {
                    return (await source.options(term)).filter(
                        (option) => !option.cssClass?.includes("o_m2o_dropdown_option_create")
                    );
                },
            },
        ];
    },
});
