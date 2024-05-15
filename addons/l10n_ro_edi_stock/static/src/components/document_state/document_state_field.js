/** @odoo-module **/
import { registry } from "@web/core/registry";

import { selectionField } from "@web/views/fields/selection/selection_field";
import { DocumentState } from "@account/components/document_state/document_state_field";

export class RoDocumentState extends DocumentState {
    get message() {
        let errors = this.props.record.data.l10n_ro_edi_stock_document_message
            ?.split("\n")
            ?.filter((error) => error?.trim()?.length > 0)

        if (errors && errors.length == 1) {
            return errors[0]
        }

        return errors?.map((error) => "• " + error)?.join("\n");
    }
}

registry.category("fields").add("l10n_ro_edi_document_state", {
    ...selectionField,
    component: RoDocumentState,
});
