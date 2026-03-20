import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { useDebounced } from "@web/core/utils/timing";
import { useService } from "@web/core/utils/hooks";
import { useState, onMounted, onPatched } from "@odoo/owl";

export const DELAY = 400;

export class AccountNumberWidget extends CharField {
    static template = "account.AccountNumberWidget";
    setup() {
        super.setup();
        this.state = useState({ label: "" });
        this.orm = useService("orm");
        this.validateAccountNumberDebounced = useDebounced(async () => {
            await this.validateAccountNumber();
        }, DELAY);

        onMounted(this.validateAccountNumber);
        onPatched(this.validateAccountNumber);
    }

    async validateAccountNumber() {
        const accountNumber = this.props.readonly ? this.formattedValue : this.input.el?.value;
        const accountType = await this.orm.call("res.partner.bank", "retrieve_account_type", [accountNumber]);
        if (["iban", "clabe"].includes(accountType)) {
            this.state.label = accountType.toUpperCase();
        } else {
            this.state.label = "";
        }
    }
}

export const accountNumberWidget = {
    ...charField,
    component: AccountNumberWidget,
};

registry.category("fields").add("account_number", accountNumberWidget);
