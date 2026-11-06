import { registry } from "@web/core/registry";
import { selectionField } from "@web/views/fields/selection/selection_field";
import { DocumentState } from "@account/components/document_state/document_state_field";

/**
 * The e-Document state pill of `account`, for a status field of the invoice or the transfer.
 * Its message is the `<status field>_message` field of the record, which the e-Document holding
 * the status fills.
 */
export class L10nTrEdiDocumentState extends DocumentState {
    // Override
    get message() {
        return this.props.record.data[`${this.props.name}_message`];
    }
}

registry.category("fields").add("l10n_tr_edi_document_state", {
    ...selectionField,
    component: L10nTrEdiDocumentState,
    fieldDependencies: ({ name }) => [{ name: `${name}_message`, type: "text", readonly: true }],
});
