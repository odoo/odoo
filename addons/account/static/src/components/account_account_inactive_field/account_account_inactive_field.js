import { extractData, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { registry } from "@web/core/registry";

function extractAccountData(record) {
    return {
        ...extractData(record),
        active: record.active,
    };
}

export class AccountAccountInactiveMany2One extends Many2One {
    static template = "account.AccountAccountInactiveMany2One";

    get many2XAutocompleteProps() {
        return {
            ...super.many2XAutocompleteProps,
            update: (records) => {
                const accountRecordData =
                    records && records[0] ? extractAccountData(records[0]) : false;
                this.update(accountRecordData);
            },
        };
    }
}

export class AccountAccountInactiveFieldMany2One extends Many2OneField {
    static components = {
        ...Many2OneField.components,
        Many2One: AccountAccountInactiveMany2One,
    };

    get m2oProps() {
        const props = super.m2oProps;
        props.cssClass = `${props.cssClass ?? ""} d-flex`;
        return {
            ...props,
            specification: { display_name: 1, active: 1 },
        };
    }
}

export const accountAccountInactiveFieldMany2One = {
    ...buildM2OFieldDescription(AccountAccountInactiveFieldMany2One),
    relatedFields: [{ name: "active", type: "bool" }],
};

registry
    .category("fields")
    .add("account_account_inactive_field", accountAccountInactiveFieldMany2One);
