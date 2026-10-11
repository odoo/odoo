import { RecipientsInput } from "@mail/core/web/recipients_input";
import { ProjectSharingRecipientTag } from "@project/project_sharing/chatter/recipient_tag";

export class ProjectSharingRecipientsInput extends RecipientsInput {
    static components = { ...RecipientsInput.components, RecipientTag: ProjectSharingRecipientTag };

    formatSuggestionLabel({ name, parent_name, email }) {
        let label = parent_name ? `${parent_name} \t --${name || ""}--` : name || "";
        if (email) {
            label = `${label} \t --${email}--`;
        }
        return label;
    }

    async fetchRecipientSuggestions(term, partnerIds) {
        const data = await this.orm.call(
            this.props.thread.model,
            "get_recipient_suggestions",
            [[this.props.thread.id]],
            { search: term || "", partner_ids: [...partnerIds] }
        );
        this.store.insert(data);
        return (data["res.partner"] || []).map((row) => ({
            ...row,
            display_name: row.name,
            __formatted_display_name: this.formatSuggestionLabel(row),
        }));
    }

    insertAdditionalRecipient(recipient) {
        super.insertAdditionalRecipient({
            ...recipient,
            persona: this.store["res.partner"].get(recipient.partner_id),
        });
    }

    getAutoCompleteSources() {
        return super.getAutoCompleteSources({ allowCreate: false, allowSearchMore: false });
    }
}
