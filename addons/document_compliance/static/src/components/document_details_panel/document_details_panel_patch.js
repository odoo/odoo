/** @odoo-module native */
import { Field } from "@web/fields/field";
import { patch } from "@web/core/utils/patch";

import { DocumentsDetailsPanel } from "@document/components/document_details_panel/document_details_panel";

DocumentsDetailsPanel.components = { ...DocumentsDetailsPanel.components, Field };

patch(DocumentsDetailsPanel.prototype, {
    get hasComplianceFields() {
        const data = this.record.data;
        return data.type !== "folder" && "document_type_id" in data;
    },

    get complianceDocumentSelected() {
        return this.hasComplianceFields && !!this.record.data.document_type_id;
    },

    get canRenew() {
        const data = this.record.data;
        return (
            this.complianceDocumentSelected &&
            data.is_renewable &&
            !data.renewed_by_document_id &&
            !this.userPermissionViewOnly
        );
    },

    selectionLabel(fieldName) {
        const value = this.record.data[fieldName];
        const selection = this.record.fields[fieldName]?.selection || [];
        return (selection.find(([key]) => key === value) || [value, value])[1];
    },

    badgeClass(tone) {
        return `badge rounded-pill ${tone || "text-bg-light"}`;
    },

    get expirationStateLabel() {
        return this.selectionLabel("expiration_state");
    },

    get expirationStateClass() {
        return this.badgeClass(
            {
                valid: "text-bg-success",
                expiring_soon: "text-bg-warning",
                expired: "text-bg-danger",
            }[this.record.data.expiration_state],
        );
    },

    get complianceStateLabel() {
        return this.selectionLabel("compliance_state");
    },

    get complianceStateClass() {
        return this.badgeClass(
            {
                compliant: "text-bg-success",
                non_compliant: "text-bg-danger",
            }[this.record.data.compliance_state],
        );
    },

    async onVerifyDocument() {
        const action = await this.orm.call(
            "document.document",
            "action_record_verification",
            [this.record.resId],
        );
        await this.props.record.load();
        return this.action.doAction(action);
    },

    async onRenewDocument() {
        const action = await this.orm.call(
            "document.document",
            "action_renew_document",
            [this.record.resId],
        );
        await this.props.record.model.load();
        return this.action.doAction(action);
    },
});
