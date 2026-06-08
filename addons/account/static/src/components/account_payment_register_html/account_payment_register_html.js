import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class AccountPaymentRegisterHtmlField extends Component {
    static props = standardFieldProps;
    static template = "account.AccountPaymentRegisterHtmlField";

    get value() {
        return this.props.record.data[this.props.name];
    }

    switchInstallmentsAmount(ev) {
        if (ev.srcElement.classList.contains("installments_switch_button")) {
            const root = this.env.model.root;
            root.update({ amount: root.data.installments_switch_amount });
        }
    }
}

const accountPaymentRegisterHtmlField = { component: AccountPaymentRegisterHtmlField };

registry.category("fields").add("account_payment_register_html", accountPaymentRegisterHtmlField);
