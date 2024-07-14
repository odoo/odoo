/** @odoo-module **/

import { registry } from "@web/core/registry";

import { selectionField } from "@web/views/fields/selection/selection_field";
import { DocumentState } from "@account/components/document_state/document_state_field";

export class MxDocumentState extends DocumentState {}

registry.category("fields").add("l10n_mx_edi_document_state", {
    ...selectionField,
    component: MxDocumentState,
});
