import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { extractData, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

/**
 * These classes and widget `many2one_bank` are meant to be
 * used only with res.partner.bank
 */

export class Many2XAutocompleteBank extends Many2XAutocomplete {
    buildRecordSuggestion(request, record) {
        const recordSuggestion = super.buildRecordSuggestion(request, record);
        const icon = record.allow_out_payment ? "fa-shield" : "fa-exclamation-circle";
        const colorClass = record.allow_out_payment ? "text-success" : "text-danger";
        const title = record.allow_out_payment ? _t("Trusted") : _t("Untrusted");
        recordSuggestion.label = markup`<i class="me-1 fa ${icon} ${colorClass}" title="${title}"></i> ${recordSuggestion.label}`;
        return recordSuggestion;
    }

    get searchSpecification() {
        return {
            ...super.searchSpecification,
            allow_out_payment: {},
        };
    }
}

function extractDataBank(record) {
    return {
        ...extractData(record),
        allow_out_payment: record.allow_out_payment,
    };
}

export class Many2OneBank extends Many2One {
    static template = "account.Many2OneBank";
    static components = {
        ...Many2One.components,
        Many2XAutocomplete: Many2XAutocompleteBank,
    };

    get many2XAutocompleteProps() {
        return {
            ...super.many2XAutocompleteProps,
            update: (records) => {
                const bankRecordData = records && records[0] ? extractDataBank(records[0]) : false;
                this.update(bankRecordData);
            },
        };
    }
}


export class Many2OneBankField extends Many2OneField {
    static components = {
        ...Many2OneField.components,
        Many2One: Many2OneBank,
    };

    get m2oProps() {
        const props = super.m2oProps;
        props.cssClass = `${props.cssClass ?? ''} d-flex`;
        return props;
    }
}

export const many2OneBankField = {
    ...buildM2OFieldDescription(Many2OneBankField),
    relatedFields: [
        { name: "allow_out_payment", type: "bool" },
    ],
};

registry.category("fields").add("many2one_bank", many2OneBankField);
