import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { useDebounced } from "@web/core/utils/timing";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onPatched, signal } from "@odoo/owl";

export const DELAY = 1000;

// Shortest account number any format can match: a Norwegian IBAN is 15 characters,
// a CLABE is 18. Below that, no need to ask the server.
const MIN_LENGTH = 15;

export class AccountNumberField extends CharField {
    static template = "web.AccountNumberField";
    setup() {
        super.setup();
        this.label = signal("");
        this.orm = useService("orm");
        this.validateAccountNumberDebounced = useDebounced(async () => {
            await this.validateAccountNumber();
        }, DELAY);

        onMounted(this.validateAccountNumber);
        onPatched(this.validateAccountNumber);
    }

    async validateAccountNumber() {
        const accountNumber = this.props.readonly ? this.formattedValue : this.input()?.value;
        if ((accountNumber || "").replace(/[\W_]/g, "").length < MIN_LENGTH) {
            this.label.set("");
            return;
        }
        const accountType = await this.orm
            .cache()
            .call("res.partner.bank", "retrieve_account_type", [accountNumber]);
        this.label.set(["iban", "clabe"].includes(accountType) ? accountType.toUpperCase() : "");
    }
}

export const accountNumberField = {
    ...charField,
    component: AccountNumberField,
};

registry.category("fields").add("account_number", accountNumberField);
