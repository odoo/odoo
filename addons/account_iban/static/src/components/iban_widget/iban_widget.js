/** @odoo-module native */
import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/fields/basic/char/char_field";
import { useDebounced } from "@web/core/utils/timing";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

export const DELAY = 400;

export class IbanWidget extends CharField {
    static template = "account_iban.iban";
    setup() {
        super.setup();
        this.state = useState({ isValidIBAN: null });
        this.orm = useService("orm");
        this.validateIbanDebounced = useDebounced(async (ev) => {
            const iban = ev.target.value;
            if (!iban) {
                this.state.isValidIBAN = null;
            } else if (!/^[A-Za-z]{2}.{3,}/.test(iban)) {
                this.state.isValidIBAN = false;
            } else {
                this.state.isValidIBAN = await this.orm.call(
                    "res.partner.bank.account",
                    "is_valid_iban",
                    [[], iban],
                );
            }
        }, DELAY);
    }
}

export const ibanWidget = {
    ...charField,
    component: IbanWidget,
};

registry.category("fields").add("iban", ibanWidget);
