/* eslint-disable no-console */
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

/**
 * Invoice Suggestion Panel — inline Accept/Reject chips for AI extraction.
 *
 * Used on the bill form as `widget="invoice_suggestion_panel"` bound to
 * `extraction_line_ids` (a one2many, so the widget gets the record's
 * `resId`, `model` and `data`). Each chip runs `orm.call` against
 * `account.move.apply_suggested_value` with exactly one field name, so a
 * single click applies exactly one value — the backend re-reads the value
 * from the persisted `extraction_json` payload, never from the client.
 *
 * The spent ("accepted" / "rejected") chips are kept locally so the panel
 * does not flicker while the form reloads; `record.load()` refreshes the
 * real data after each apply.
 */
export class InvoiceSuggestionPanel extends Component {
    static template = "invoice_agent.suggestion_panel";

    static props = {
        record: Object,
        fieldInfo: { type: Object, optional: true },
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            applying: new Set(), // field_name -> call in flight
            spent: new Set(), // field_name -> accepted or rejected this session
        });
    }

    // ------------------------------------------------------------------
    // State
    // ------------------------------------------------------------------
    get suggestions() {
        const fieldName = this.props.fieldInfo?.name;
        if (!fieldName) {
            return [];
        }
        const data = this.props.record?.data?.[fieldName] || {};
        return (data.records || []).filter(
            (suggestion) => !this.state.spent.has(suggestion.data?.field_name)
        );
    }

    get busy() {
        return this.state.applying.size > 0;
    }

    get disabled() {
        return this.props.readonly || this.busy;
    }

    // ------------------------------------------------------------------
    // Actions
    // ------------------------------------------------------------------
    async acceptSuggestion(suggestion) {
        const fieldName = suggestion.data?.field_name;
        if (!fieldName || this.state.applying.has(fieldName)) {
            return; // double-click guard: one call per field
        }
        this.state.applying.add(fieldName);
        try {
            await this.orm.call(
                this.props.record.model,
                "apply_suggested_value",
                [this.props.record.resId],
                { field_name: fieldName }
            );
            this.state.spent.add(fieldName);
        } catch (error) {
            // Keep the chip visible so the accountant can retry after fixing
            // the underlying issue (e.g. vendor not found).
            console.warn("invoice_agent: apply_suggested_value failed", error);
            throw error;
        } finally {
            this.state.applying.delete(fieldName);
        }
        await this.props.record.load();
    }

    async rejectSuggestion(suggestion) {
        const fieldName = suggestion.data?.field_name;
        if (!fieldName || this.state.applying.has(fieldName)) {
            return;
        }
        this.state.spent.add(fieldName);
        // Rejection is purely local: no backend write. A later "Suggest with
        // AI" run regenerates the full suggestion set.
    }
}

// Register the widget so `widget="invoice_suggestion_panel"` resolves. The
// panel binds to the `extraction_line_ids` one2many, whose records expose
// `data.field_name`, `data.extracted_value` and `data.field_confidence`.
export const invoiceSuggestionPanel = {
    component: InvoiceSuggestionPanel,
    supportedTypes: ["one2many"],
    relatedFields: [
        { name: "field_name", type: "char" },
        { name: "extracted_value", type: "text" },
        { name: "field_confidence", type: "float" },
    ],
    extractProps({ attrs }) {
        return {
            readonly: attrs.readonly ? attrs.readonly === "True" : false,
        };
    },
};

registry.category("fields").add("invoice_suggestion_panel", invoiceSuggestionPanel);